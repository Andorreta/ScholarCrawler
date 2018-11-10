# ScholarCrawler

Google Scholar Web page crawler
***
## Estructura de las clases del proyecto:
* **Models**: Contiene las factorias para poder almacenar los datos. (MongoDB y Memoria RAM)
* **Crawler**: Contiene los crawler para los diferentes portales.
    * **httpProviders**: Aqui vamos a poner todos los metodos para descargar los datos (Proxies, webDrivers, etc)
        * **proxyTor**: Aqui voy a poner las funciones para controlar Tor y no dejarlo funcionar sin supervisión, para obtener los mejores resultados posibles
    * **General**: Funciones generales como el tratamiento de errores (deteccion de datos vacios y captchas) y las funciones genericas de extraccion de datos. De ese modo solo hay que poner las funciones especificas del crawler y susbtituir las genericas dentro de cada clase.
    * **GoogleScholarArticles**: Crawler con las funciones especificas para extraer los datos de Google Scholar. Contiene las funciones tanto de extraccion como de procesamiento de datos.
    * **Orcid**: Crawler para coger los datos de los apodos de los profesores de Orcid. Contiene las funciones de extraccion especificas y de procesamiento.
***
## Pasos a Realizar:
* Convertir el fichero inmenso del crawler en varios subficheros. (Para el de articulos y el orcid y un posible SPIDER)
* Añadir un timer que ejecute la descarga de las tareas programadas 2 veces a la semana.
    * Usar el APScheduler, para añadir los jobs usando un mongo jobstore y cuando se modifiquen los datos del job en mongo modificar el job del cron.
    * Tambien hay que hacer que borre todos los jobs y los recree desde el jobstore de mongo una vez al dia.
* Hacer que las peticiones a la API (las descagas...) sean asyncronas.
    * Se puede hacer ejecutando el crawler desde el Shell
    * Tambien se puede hacer usando el scheduler para que lanze las tareas con una programación inmediata y sin repetición ***(Mejor opcion)*** 
* Añadir una pagina de configuracion para permitir cambiar los tiempos de descaga y los IDs y datos de los usuarios (mail, password, tiempo de descarga y scholar_ids).
    * Como minimo hacer la función de la API para poder cambiar la configuración, así si me encallo en la parte visual no va a pasar nada, porque ya tendré la función hecha.
* Añadir una tabla nueva, que se pueda consultar en una pestaña dentro de la pagina de los articulos, para poder ver los articulos descartados, debido a que no se ha encontrado el ID que se buscaba.
* Separar las funciones de los crawlers para permitir herencia. Es decir, sacar mierda del ***\_\_init\_\_.py*** y meterlo dentro del ***GoogleScholar.py*** y lo generico, como lo del TOR, en el ***crawlerGeneral.py***.
* Añadir el crawler de Orcid para coger los datos de los Ids de los profesores. ***(OPCIONAL)***
* Añadir una comprobación en el models/factory de que si no se puede conectar a MongoDB, que use el modelo de memoria.

## Update 2018-11-10:
* He conseguido hacer funcionar el ProxyTor y añadir un control de errores un poco mas complejo.
    * **POR HACER:** Hay un fallo cuando sale un captcha, parece que proxy cambia de IP, pero no repite la ultima request, por lo que nos manda a la pagina principal de google scholar y se queda en bucle infinito allí.