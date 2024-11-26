# Dockerfile
FROM python:3.9-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    libpq-dev \  
    build-essential \
    zlib1g-dev \ 
    wget \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Descargamos el código fuente de OpenSSL
RUN wget https://www.openssl.org/source/openssl-1.1.1w.tar.gz \
    && tar -xvzf openssl-1.1.1w.tar.gz \
    && cd openssl-1.1.1w \
    # Configuramos y compilamos OpenSSL
    && ./config --prefix=/usr/local/ssl --openssldir=/usr/local/ssl shared zlib \
    && make \
    && make install \
    # Limpiamos los archivos de compilación para reducir el tamaño de la imagen
    && cd .. \
    && rm -rf openssl-1.1.1w openssl-1.1.1w.tar.gz

# Configuramos las bibliotecas dinámicas
RUN echo "/usr/local/ssl/lib" > /etc/ld.so.conf.d/openssl.conf \
    && ldconfig

# Actualizamos el PATH para que apunte a la nueva versión de OpenSSL
ENV PATH="/usr/local/ssl/bin:$PATH"

# Verificamos la versión instalada de OpenSSL
RUN openssl version

# Cambiar configuración de OpenSSL (si es necesario)
RUN sed -i 's/^\(MinProtocol *=.*\)/#\1/' /etc/ssl/openssl.cnf && \
    sed -i 's/^\(CipherString *=.*\)/#\1/' /etc/ssl/openssl.cnf && \
    echo 'MinProtocol = TLSv1.0\nCipherString = DEFAULT:@SECLEVEL=1' >> /etc/ssl/openssl.cnf

# Establecer directorio de trabajo
WORKDIR /app

# Copiar y instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . /app/

# Exponer el puerto
EXPOSE 8000

# Comando por defecto para iniciar la aplicación
CMD ["runserver", "--bind", "0.0.0.0:8000", "api.wsgi:application"]
