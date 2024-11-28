import json, os, time, subprocess,glob, base64

from requests import Session
from pathlib import Path
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver import Firefox, FirefoxProfile, FirefoxOptions
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib3 import Retry
import logging

from rest_framework.permissions import IsAuthenticated 
from django.views import View
from django.http import HttpResponse


logger=logging.getLogger(__file__)

BASE_DIR=Path(__file__).parent.parent.parent.parent.resolve()
files_path=os.path.join(BASE_DIR,'data/')
type_doc = ["33","43","46","56","61"]
# Create your views here.

class GenerateCaf(View):

    permission_classes = (IsAuthenticated,)
    

    def post(self, request, *args, **kwargs):
        # Se recibe un json con los siguientes datos
        # rut certificado, clave certificado, ambiente, tipo de documento, cantidad de folios, datos de la empresa {rut,nombre}
        
        request_data = json.loads(request.POST['input'])
        pfx_file = request.FILES['files']  # Archivo pfx
        rut = request_data['RutCertificado']
        password = request_data.get('Password',None)
        company_rut = request_data.get('RutEmpresa',None)
        ambiente = request_data.get('Ambiente',0)
        cod_doc = request_data.get('folio_type', '2')
        cant_folios = request_data.get('quantity', '100000')

        try:
            # Guardar el archivo PFX en el sistema de archivos
            pfx_path = os.path.join(files_path, 'certificados', pfx_file.name)
            with open(pfx_path, 'wb') as f:
                for chunk in pfx_file.chunks():
                    f.write(chunk)
        except Exception as e:
            print(f"Error saving PFX file: {e}")

        # documentos con maximo       

        url_inicio ='https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi'
       
        if ambiente == 1:
            url_folios= 'https://palena.sii.cl/cvc_cgi/dte/of_solicita_folios'
        elif ambiente == 0:
            url_folios = 'https://maullin.sii.cl/cvc_cgi/dte/of_solicita_folios'   
        else:
            response={}
            response['estado']='Error'
            response['msg']='Ambiente incorrecto'
            return HttpResponse(json.dumps(response))

        estado = self.request.user

        if estado is None:
            # l = Log(user=rut,msg=' Intenta utilizar servicios sin permisos', service='check_status')
            # l.save()
            # er = Errors(user=rut,msg=' Intenta utilizar servicios sin permisos', service='check_status')
            # er.save()
            logger.info(msg=rut+'-Intenta utilizar servicios sin permisos')
            response={}
            response['estado']='Error'
            response['msg']=estado
            return HttpResponse(json.dumps(response))

        # l = Log(user=rut,msg=' solicita '+cant_folios+' folios', service='PedirFolios')
        # l.save()
        logger.info(msg=rut+'-Solicita '+str(cant_folios)+' folios')

        cookies = self.login(rut_cliente=rut, password= password, company_rut=company_rut, pfx_path=pfx_path)
        
        firefox_opt = Options() #FirefoxOptions()
        firefox_opt.headless=True
        firefox_opt.add_argument("--headless")
        firefox_prof = FirefoxProfile(profile_directory=os.path.join(files_path,'profile'))
        firefox_prof.set_preference("browser.download.manager.showWhenStarting", False)
        firefox_prof.set_preference("browser.download.folderList",2)
        firefox_prof.set_preference("browser.download.dir", os.path.join(files_path,'downloads'))
        firefox_prof.set_preference("browser.download.useDownloadDir", True)
        firefox_prof.set_preference("browser.download.viewableInternally.enabledTypes", "")
        firefox_prof.set_preference("browser.helperApps.neverAsk.saveToDisk",
                               "text/xml,application/xml,application/octet-stream")
        
        # Configurar la estrategia de carga de página
        firefox_opt.page_load_strategy = 'eager'  # Puede ser 'normal', 'eager' o 'none'

        # Añadir el perfil a las opciones
        firefox_opt.profile = firefox_prof

        driver_path=os.path.join(files_path,'driver/geckodriver')
        rut,dv = company_rut.split('-')
        try:
            # Crear un servicio para el controlador
            service = Service(executable_path=driver_path)
            # Inicializar el controlador Firefox con el servicio y las opciones
            print('Iniciando driver')
            driver = Firefox(service=service, options=firefox_opt)
            print('Driver iniciado')
            # Esperar a que la página se cargue completamente
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    
            # Navegar al dominio correcto antes de agregar las cookies
            driver.get(url_inicio)
            for cookie in cookies:
                driver.add_cookie({
                    'name': cookie.name,
                    'value': cookie.value,
                    'path': '/',
                    'domain': 'sii.cl'
                })
            # print('cookies driver post get:\n' , driver.get_cookies(),'\n\n')
            driver.get(url_folios)
                       
            input_rut = WebDriverWait(driver,10).until(EC.element_to_be_clickable ((By.XPATH,'/html/body/form/center/table/tbody/tr/td[2]/input[1]')))
            input_dv = WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.XPATH,'/html/body/form/center/table/tbody/tr/td[2]/input[2]')))
            input_rut.send_keys(str(rut))
            input_dv.send_keys(str(dv))
            driver.find_element(By.NAME,'ACEPTAR').click()                           
        except  Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")
            if driver:
                driver.close()
            # l=Log(user = rut,msg =' Error en el driver,no se aceptan las cookies', service='PedirFolios')
            # l.save()
            # er=Errors(user = rut,msg=' Error en el driver,no se aceptan las cookies', service='PedirFolios')
            # er.save()
            logger.info(msg = rut+dv+'-Error en el driver,no se aceptan las cookies')
            response={}
            response['estado']='Error'
            response['msg']='Driver no acepta cookies'
            return HttpResponse(json.dumps(response))
        
        print('Se solicita el folio')
        try:
            select_doc = Select(WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.NAME,'COD_DOCTO'))))
            select_doc.select_by_value(str(cod_doc))
            if cod_doc in type_doc:
                #El documento elegido tiene maximo de folios
                max_folios = WebDriverWait(driver,5).until(EC.presence_of_element_located((By.NAME,'MAX_AUTOR'))).get_attribute('value')
                input_cant_folios = WebDriverWait(driver,5).until(EC.presence_of_element_located((By.NAME,'CANT_DOCTOS')))
                if max_folios < cant_folios:
                    driver.close()
                    # l=Log(user = rut,msg =' solicita mas folios del maximo permitido', service='PedirFolios')
                    # l.save()
                    logger.info(msg = rut+'-Solicita mas folios del maximo permitido')
                    # er=Errors(user = rut,msg=' solicita mas folios del maximo permitido', service='PedirFolios')
                    # er.save()
                    response={}
                    response['estado']='Error'
                    response['msg']='La cantidad de folios supera el maximo permitido.\n Maximo folios: ' + str(max_folios)
                    return HttpResponse(json.dumps(response))
                else:
                    input_cant_folios.send_keys(str(cant_folios))      
            else:                
                input_cant_folios= WebDriverWait(driver,10).until(EC.presence_of_element_located((By.NAME,'CANT_DOCTOS')))
                input_cant_folios.send_keys(str(cant_folios))
            #Probar si se encuentra alguna alerta o error
            WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.NAME,'ACEPTAR'))).click()

        except Exception as e:
            print('error en la solicitud de folios:',e)
            text_box=WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'/html/body/center[2]')))
            response={}
            response['estado']='Error'
            response['msg'] = f'{text_box.text} \n || {e}'
            driver.close()
            return HttpResponse(json.dumps(response))
    
        try:
            WebDriverWait(driver,2).until(EC.alert_is_present())
            print('alerta')
            alert=driver.switch_to.alert
            texto=alert.text
            alert.accept()
            # l=Log(user=rut,msg=' Se detecto una alerta', service='PedirFolios')
            # l.save()
            # er=Errors(user=rut,msg=' Se detecto una alerta' , service='PedirFolios')
            # er.save()
            logger.info(msg=rut+'-'+ texto)
            response={}
            response['estado']='Error'
            response['msg']=texto
            driver.close()
            return HttpResponse(json.dumps(response))
                                
        except TimeoutException:
            print('descargar xml')
            # cuando la pagina sea la correcta se descarga el archivo
            WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.NAME,'ACEPTAR'))).click()
            print('Descargar XML de folio')
            boton_descarga = WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.NAME,'ACEPTAR')))
            boton_descarga.click() 
            # Retornar archivo
            company_rut_split =company_rut.split('-')[0]
            files=glob.glob(os.path.join(files_path,f'downloads/*{company_rut_split}*.xml'))
            max_file = max(files,key=os.path.getctime)
            with open(max_file,'r', encoding='ISO-8859-1') as f:
                xml=f.read()
                print(xml)
            print("archivo descargado:", xml)
            response = HttpResponse(xml, content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename="response.xml"'
            return response
            # responder base64
            # with open(max_file,'rb') as f:
            #     data=f.read()
            #     print(data)
            #     b64=base64.encodebytes(data).decode("utf-8")
            #     b64=b64.replace('\n','')
            # # l=Log(user=rut,msg=' Finaliza correctamente', service='PedirFolios')
            # # l.save()
            # # logger.info(msg=rut+'-PedirFolios finaliza correctamente')
            # # driver.close()
            # response={}
            # response['estado']='Ok'
            # response['msg']='Finaliza correctamente'
            # response['xml']= b64
            # return HttpResponse(json.dumps(response))      
        

    def convert_pfx_to_pem(self, pfx_path, pem_path, password=None):
        try:
            command = ['openssl', 'pkcs12', '-in', pfx_path, '-out', pem_path, '-nodes']
            print(command)
            if password:
                command.extend(['-password', f'pass:{password}'])
            subprocess.run(command, check=True)
            return pem_path
        except subprocess.CalledProcessError as e:
            print(f"Error converting PFX to PEM: {e}")
            return None
    
    def login(self,rut_cliente, password,company_rut, pfx_path):
        rut,dv= rut_cliente.split('-')
        url_inicio='https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi'

        logger.info(msg='login de usuario:'+rut_cliente + ' con password: '+password)
        try:
            
           
            timestamp = int(time.time())
            pem_path = os.path.join(BASE_DIR, 'data', f'{timestamp}_{company_rut}.pem')
            
            # Convert PFX to PEM
            pem_path = self.convert_pfx_to_pem(pfx_path, pem_path, password=password)
            if not pem_path:
                raise Exception("Failed to convert PFX to PEM")


            install_path = os.path.join(BASE_DIR, 'data/Install_certificate.sh')
            print(install_path, pem_path)
            subprocess.run(['bash', install_path, pem_path, company_rut])
            # print('La instalacion finalizo con codigo:', cert_install.returncode)
        except Exception as e:
            logger.error(f"Error during login: {e}")
            response={}
            response['estado']='Error'
            response['msg']='Error al encontrar la compañia o instalar certificados. Compruebe e intente nuevamente'
            return HttpResponse(json.dumps(response))
        try:
        #Probando con requests
            s=Session()
            s.get(url_inicio) 
            url_post = 'https://herculesr.sii.cl/cgi_AUT2000/CAutInicio.cgi?https://misiir.sii.cl/cgi_misii/siihome.cgi'
            s.post(url_post,cert=pem_path, allow_redirects=True, data={'rut' : rut,
                    'referencia' : 'https://www.sii.cl',
                    'dv': dv})
            time.sleep(1)
            s.get('https://maullin.sii.cl/cvc_cgi/dte/of_solicita_folios')
            cookies=s.cookies 
            s.close()
            return cookies
        except:
            response={}
            response['estado']='Error'
            response['msg']='Error al conseguir las credenciales de acceso SII'
            return HttpResponse(json.dumps(response)) 

