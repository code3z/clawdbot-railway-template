c

| ![][image1] | Weather Company Data  |  Data Visualization \- Weather Imagery  |  Common Usage Guide Domain Portfolio: Weather Imagery  |  Domain: Common  |  API Name: Data Visualization \- Common Usage Guide Standard HTTP Cache-Control headers are used to define caching length. The TTL value is provided in the HTTP Header as an absolute time value using the “Expires” parameter.  Example:  “Expires: Fri, 12 Jul 2013 12:00:00 GMT”.    |
| :---- | ----- |

### **Overview**

| The ‘Tiler’, and ‘Featurizer’ products support data visualization and analytics.  Tiler provides gridded raster data as binary buffers of big-endian 4-byte floating point values, typically in tiles of 256x256 pixels at various levels of detail; a client-side SDK can use this data to create weather image tiles Featurizer provides geometric vector data, either a line or a polygon, indicating where meteorological values cross a particular threshold; this data can facilitate statistical analysis Using the Tiler and Featurizer products require a multi-step workflow to retrieve the necessary data for the specific product data request. Steps 2a, and 2b are dependent on which type you are requesting (i.e. Tiler Data or Featurizer Tile. Both step 2a, and step 2b require the ‘t’ parameter values as input into the ‘t’ parameter for the subsequent request (v2/tiler/data, and v2/featurizer/tile). Step 1: Get Tiler Info \- Provides current dimensions ‘t’ and ‘rt’ parameter values on one or more products. Step 2a: Get Tiler Data \- Provides tiles of meteorological data from one or more products. Step 2b: Get Featurizer Tile \- Provides a polygon or line indicating when a product’s data has crossed a given threshold, in web-mercator projection. | Conceptual Visualization  Gridded Data from Tiler ![SSDS Overview Images\_tiler\_b-and-w\_cropped-2.jpg][image2] | Conceptual Visualization  Vector Data from Featurizer ![Document-Relationships\_featurizer\_cropped.jpg][image3] *Area with values ≥ 2.0* |
| :---- | :---: | :---: |

**URL Construction**

| Step 1: Get Tiler Info |
| :---- |
| **Tiler Info: Required Parameters:**  **products,** apiKey\=**yourApiKey  ||  Optional Parameters:** meta=true https://api.weather.com/v2/tiler/info?products=**\<productNumber\>:\<variableID\>**&**apiKey=yourApiKeytiler** |
| The \[**v2/tiler/info?**\] request response provides the **‘t’** parameter value required as input for the subsequent \[**v2/tiler/data?**\] request as well as a subsequent \[**v2/featurizer/tile?**\] request. If the product is an ‘Observation/Current Condition’ type then it will return a **‘t’** parameter value; if the product is a ‘Forecast’ type then it will return both a **‘t’** parameter value and **‘rt’** parameter value. Note: some exceptions may apply to the use of the **‘t’** parameter value and **‘rt’** parameter values; please see product specific details for all product specific required and optional parameters. The meta=true additional information helps to provide available **lod**, **x**, and **y** parameters to use in subsequent requests. |
| https://api.weather.com/v2/tiler/info?products=17:VAR00198FROM25501heightaboveground\&meta=true\&apiKey=yourApiKey |
| **Step 2a: Get Tiler Data** |
| **Tiler Data \- Observations: Required Parameters:**  **products, t, lod, x, y,** apiKey\=**yourApiKey** https://api.weather.com/v2/tiler/data?products=**\<productNumber\>:\<variableID\>**\&t=**\<t\>**\&lod=**\<lod\>**\&x=**\<x\>**\&y=**\<y\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/tiler/data?products=17:VAR00198FROM25501heightaboveground\&t=**1474300200000**\&lod=1\&x=0\&y=0\&apiKey=yourApiKey |
| **Tiler Data \- Forecast: Required Parameters:**  **products, rt, t, lod, x, y,** apiKey\=**yourApiKey** https://api.weather.com/v2/tiler/data?products=**\<productNumber\>:\<variableID\>**\&rt=**\<rt\>**\&t=**\<t\>**\&lod=**\<lod\>**\&x=**\<x\>**\&y=**\<y\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/tiler/data?products=49:Temperatureheightaboveground\&rt=**1474375500000**\&t=**1474400700000**\&lod=1\&x=0\&y=0\&apiKey=yourApiKey |
| **Step 2b: Get Featurizer Tile** |
| **Featurizer Tile \- Observations: Required Parameters:**  **product, t, lod, x, y,** apiKey\=**yourApiKey  ||  Optional Parameters:** threshold https://api.weather.com/v2/featurizer/tile?product=**\<productNumber\>:\<variableID\>**\&t=**\<t\>**\&lod=**\<lod\>**\&x=**\<x\>**\&y=**\<y\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/featurizer/tile?product=17:VAR00198FROM25501heightaboveground\&t=**1474300200000**\&lod=4\&x=2\&y=4\&threshold=280\&apiKey=yourApiKey |
| **Featurizer Feature (Native Resolution) \- Observations: Required Parameters:**  **product, t,** apiKey\=**yourApiKey  ||  Optional Parameters:** threshold https://api.weather.com/v2/featurizer/feature?product=**\<productNumber\>:\<variableID\>**\&t=**\<t\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/featurizer/feature?product=17:VAR00198FROM25501heightaboveground\&t=**1474300200000**\&threshold=280\&apiKey=yourApiKey |
| **Featurizer Tile \- Forecast: Required Parameters:**  **product, rt, t, lod, x, y,** apiKey\=**yourApiKey  ||  Optional Parameters:** threshold https://api.weather.com/v2/featurizer/tile?product=**\<productNumber\>:\<variableID\>**\&rt=**\<rt\>**\&t=**\<t\>**\&lod=**\<lod\>**\&x=**\<x\>**\&y=**\<y\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/featurizer/tile?product=49:Temperatureheightaboveground\&rt=**1474375500000**\&t=**1474400700000**\&lod=1\&x=0\&y=0\&threshold=280\&apiKey=yourApiKey |
| **Featurizer Feature (Native Resolution) \- Forecast: Required Parameters:**  **product, rt, t,** apiKey\=**yourApiKey  ||  Optional Parameters:** threshold https://api.weather.com/v2/featurizer/feature?product=**\<productNumber\>:\<variableID\>**\&rt=**\<rt\>**\&t=**\<t\>**&**apiKey=yourApiKey** |
| https://api.weather.com/v2/featurizer/feature?product=49:Temperatureheightaboveground\&rt=**1474375500000**\&t=**1474400700000**\&threshold=280\&apiKey=yourApiKey |

### Using Tiler Info & Parameters

The Tiler Info API is used to retrieve current details about one or more products. By calling the v2/tiler/info API with the optional parameter ‘meta=true’, the details about each requested product’s native projection and valid Web Mercator tiles are delivered in the response.

* **NOTE**: All API requests for this endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* The ‘products’ parameter can accept up to fifteen (15) comma-delimited values:  
  * Example: products=1:Precipitationtypesurface,6:VAR01515FROM25011surface,19,20  
  * Sample: https://api.weather.com/v2/tiler/info?products=1:Precipitationtypesurface,6:VAR01515FROM25011surface,19,20\&apiKey=yourApiKey

* To retrieve the details on exactly one type of data from a product number, include the product number and the variable ID separated by a colon:   
  * Example: products=303:tdprob  
  * Sample: https://api.weather.com/v2/tiler/info?products=303:tdprob\&apiKey=yourApiKey

* To retrieve the details on all data associated with a product number, include this number while omitting any variable IDs:   
  * Example: products=303  
  * Sample: [https://api.weather.com/v2/tiler/info?products=303\&apiKey=yourApiKey](https://api.weather.com/v2/tiler/info?products=303&apiKey=yourApiKey)

### Using Tiler Data & Parameters

The Tiler Data API retrieves tiles of meteorological data from one or more products.

* **NOTE**: All API requests for this endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* products: the ‘products’ parameter for this endpoint must include both the product number and the variable ID, separated by a colon:   
  * Example: products=300:PrecipIntensity  
  * Sample: https://api.weather.com/v2/tiler/data?products=300:PrecipIntensity\&t=1451606400000\&lod=4\&x=4\&y=6\&apiKey=yourApiKey  
* dimension: the dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* *lod, x, y*:  the combination of these tile parameters must correspond to a tile within the product’s tileset, found by calling /tiler/info?meta=true  
* For the product’s native resolution, set lod to \-1, and for the Web Mercator projection, use any valid lod value where lod ≥ 0

### Using Tiler Byte & Parameters

The Tiler Byte API retrieves a byteset object that contains information regarding the values contained in each tile at all levels of detail for a single time value. Data includes minimum value and maximum value for the tile and whether there are empty cells (NaN values) in the tile.  

* **NOTE**: All API requests for this endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* products: the *‘products’* parameter for this endpoint must include both the product number and the variable ID, separated by a colon:   
  * Example: products=300:PrecipIntensity  
  * Sample: https://api.weather.com/v2/tiler/byte?products=300:PrecipIntensity\&t=1451606400000\&raw=false\&apiKey=yourApiKey  
* dimension: the dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* If *raw* is true, then the native layer byteset is returned. If raw is not given or is false, then the Web Mercator byteset for the pyramid is returned. 

The entire pyramid (all LODs) of the tiles is returned concatenated in ascending raster-order (i.e. info for lod=0,x=0,y=0 (0,0,0) followed by lod=1,x=0,y=0 (1,0,0), (1,0,1), (1,1,0), (1,1,1), (2,0,0) and so on. Each tile is described by a record of up to 3 floating point values. If the first 4 bytes make up a floating point value of not-a-number, then the record is only 4 bytes long and the tile has no data. Calling Tiler API for such tiles should result in a 400 response. If the first 4 bytes do not make up a not-a-number value, then the record is 9 bytes long and should be decoded as follows.

1. The first 4 bytes make up the floating point value for the minimum value in the tile.  
2. The second 4 bytes make up a floating point value that is the maximum value in the tile.  
3. The last byte is a boolean that describes if any cells in the tile are empty, that is, the cell value is not-a-number.

### Using Tiler Coverage & Parameters

The Tiler Coverage API retrieves a bitset object that contains a single bit for each tile at all levels of detail for a single time value. This bit flag denotes whether the given tile exists at that LOD and x, y.

* **NOTE**: All API requests for this endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* products: the ‘products’ parameter for this endpoint must include both the product number and the variable ID, separated by a colon:   
  * Example: products=300:PrecipIntensity  
  * Sample: https://api.weather.com/v2/tiler/coverage?products=300:PrecipIntensity\&t=1451606400000\&apiKey=yourApiKey  
* dimension: the dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* If *raw* is true, then the native layer bitset is returned. If raw is not given or is false, then the Web Mercator bitset for the pyramid is returned. **Note** that coverage data is typically not produced for the native layer. The API allows such requests, but a response will often be an error.

### The entire pyramid (all LODs) of the tiles is returned concatenated in ascending raster-order (i.e. info for lod=0,x=0,y=0 (0,0,0) followed by lod=1,x=0,y=0 (1,0,0), (1,1,0), (1,0,1), (1,1,1), (2,0,0) and so on. Each tile is described by a single bit packed in reverse order into bytes.

### Using Tiler Extras Data & Parameters

The Tiler Extras Data API returns the same data as the /tiler/data call discussed above except that it allows the user to choose to receive data only over the oceans or only over land. This API may also be used to provide interpolated tile data at LODs otherwise not supported for a given product. See “Geographic Coverage” for more information on LODs available.

* **NOTE**: All API requests for this endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* products: the ‘products’ parameter for this endpoint must include both the product number and the variable ID, separated by a colon:   
  * Example: products=300:PrecipIntensity  
  * Sample: [https://api.weather.com/v2/tiler/extras/data?products=300:PrecipIntensity\&stencil=true&](https://api.weather.com/v2/tiler/extras/data?products=300:PrecipIntensity&stencil=true&)interpolation=bicubic\&t=1451606400000\&lod=4\&x=4\&y=6\&apiKey=yourApiKey  
* dimension: the dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* *lod, x, y*:  the combination of these tile parameters must correspond to a tile within the product’s tileset, found by calling /tiler/info?meta=true  
* Optional Parameters: stencil, interpolation  
* This API should only be used for the Web Mercator projection, i.e. lod value ≥ 0

### Using Featurizer Tile & Parameters

The Featurizer Tile API retrieves a polygon or line tracing a particular threshold for a product’s data, for a single tile in Web Mercator projection.

* **NOTE**: All API requests for the first endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* product: the ‘product’ parameter must include both the product number and the variable ID, separated by a colon:   
  * Example: product=300:PrecipIntensity  
  * Sample: https://api.weather.com/v2/featurizer/tile?product=300:PrecipIntensity\&t=1451606400000\&lod=4\&x=4\&y=6\&apiKey=yourApiKey  
* \<dimensions\>: dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* lod, x, y:  the combination of these tile parameters must correspond to a tile within the product’s tileset, found by calling /tiler/info?meta=true  
* The lod parameter must indicate the Web Mercator projection, where lod ≥ 0  
  * To request the product’s native resolution, use the featurizer/feature endpoints  
* Optional Parameters: operation, threshold, replacement, geometryType, crs, bbox

The API returns a geographic feature, namely a polygon or line as defined by the geometryType parameter.  The API examines each pixel in the requested tile against the operation and threshold values, and the resulting feature corresponds to the area where the comparison evaluates to “true.”

The type of the response depends on the specific endpoint that is called, as documented below.

| REQUIRED: All API responses must be compressed. The kmz, XZipped shp, and mvt file formats are compressed by definition; API requests for JSON objects, GeoJSON objects, and arrays of primitive data types must include the following HTTP header: “Accept-Encoding: gzip". |  |  |
| :---- | :---- | :---- |
| Endpoint | Response  | MIME Content-Type |
| /tile | GeoJSON | application/json (gzipped) |
| /tile:kmz | .kmz | application/vnd.google-earth.kmz |
| /tile:shp | XZipped .shp | application/x-zipped-shp |
| /tile:mvt | .mvt | application/x-vector-tile |

### Using Featurizer Feature & Parameters

The Featurizer Feature API retrieves a polygon or line tracing a particular threshold for a product’s data, for all data in the product’s native projection.

* products: for this endpoint, this parameter must include both the product number and the variable ID, separated by a colon:   
  * Example: products=300:PrecipIntensity  
  * Sample: https://api.weather.com/v2/featurizer/feature?product=300:PrecipIntensity\&t=1451606400000\&apiKey=yourApiKey  
* \<dimensions\>: dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* Optional Parameters: operation, threshold, replacement, geometryType, crs, bbox

The API returns a geographic feature, namely a polygon or line as defined by the geometryType parameter.  The API examines each pixel in the product’s native projection against the operation and threshold values, and the resulting feature corresponds to the area where the comparison evaluates to “true.”

The type of the response depends on the specific endpoint that is called, as documented below.

| REQUIRED: All API responses must be compressed. The .kmz, XZipped.shp, and .mvt file formats are compressed by definition; API requests for JSON objects, GeoJSON objects, and arrays of primitive data types must include the following HTTP header: “Accept-Encoding: gzip". |  |  |
| :---- | :---- | :---- |
| Endpoint | Response  | MIME Content-Type |
| /feature | GeoJSON | application/json (gzipped) |
| /feature:kmz | .kmz | application/vnd.google-earth.kmz |
| /feature:shp | XZipped .shp | application/x-zipped-shp |

### Using Featurizer Isoband & Parameters

The Featurizer Isoband API retrieves polygons containing all data between a lower and upper threshold, for all data in the product’s native projection.

* **NOTE**: All API requests for the first endpoint are required to include the following header, prompting the system to compress the response: “Accept-Encoding: gzip”.  
* product: the ‘product’ parameter must include both the product number and the variable ID, separated by a colon:   
  * Example: product=6:VAR01515FROM25011surface  
  * Sample: https://api.weather.com/v2/featurizer/isoband?product=6:VAR01515FROM25011surface\&threshold=35.0:40.0\&t=1451606400000\&apiKey=yourApiKey  
* \<dimensions\>: dimensions vary by API product, and valid dimensions can be found by calling /tiler/info  
* *threshold*: this should be two floating point values for lower and upper bounds, separated by a colon, e.g. threshold=35.0:40.0  
* Optional Parameters: replacement, crs, bbox, format  
* Unsupported parameters: lod, x, y

### 

### Query Parameter Elements & Definitions

| Parameter Name | Description | Is Required | Sample |
| :---- | :---- | :---: | :---- |
| apiKey | Client's API Key | **Required** | apiKey=**yourApiKey** |
| lod | Level of Detail (LOD), also known as the zoom level. The metadata found by calling /tiler/info provides more details about the valid ranges of lod, x, and y for a particular product. The product’s native LOD can be invoked with lod=-1.  A global image tile can be invoked for the lowest LOD with lod=0. The single image tile at lod=0 encompasses the entire globe in Web Mercator projection, and each subsequent LOD doubles: Zoom (level of detail) Range of possible x values Range of possible y values  | **Required** | lod=4 |
| rt | "Run time" Timestamp, in milliseconds \- Required parameter for 'Forecast' type products. | **Required** | rt=1451649600000 |
| t | Timestamp, in milliseconds | **Required** | t=1451649600000 |
| x | Horizontal tile position | **Required** | x=4 |
| y | Vertical tile position | **Required** | y=6 |
| **Tiler APIs \- Parameters Unique To Tiler** |  |  |  |
| Parameter Name | Description | Is Required | Sample |
| products | Products (plural) used in the tiler APIs. Specific API products, where each is typically referenced with a colon-separated Product Number and Variable ID | **Required** | products=303:tdprob |
| meta | Request to display metadata, for /tiler/info The metadata found by calling /tiler/info provides more details about the valid ranges of lod, x, and y for a particular product. For example, a geographically limited product may further restrict the valid ranges for x and y to include only those tiles that cover the product’s region. | Optional | meta=true |
| **Featurizer APIs \- Parameters Unique To Featurizer** |  |  |  |
| Parameter Name | Description | Is Required | Sample |
| product | Product (singular) Specific API product requested in the featurizer APIs | **Required** | product=303:tdprob |
| bbox | Comma-delimited string of decimal pair of x-y coordinates, restricting the area subject to analysis by Featurizer. These coordinates set the **lower-left (southwest)** and **upper-right (northeast)** corners of the rectangular bounding box that Featurizer will examine, and its values must be (**long,lat,long,lat**), with the lower-left corner defined first. **NOTE** that the order of the coordinates is (x,y) \-- longitude, latitude \--  which is consistent with the GeoJSON convention. | Optional | bbox=-129.4,21.37,-64.56,50.35 |
| crs | Type of coordinate reference system used to define the projection of the GeoJSON geometry object returned by Featurizer **Default Value:** EPSG:4326 **Accepted Values:** Any EPSG code, such as EPSG:4326 or EPSG:3857 The default crs value of EPSG:4326 corresponds to WGS 84, a standard established in 1984 as part of the the World Geodetic System developed by the US Department of Defense. Information on EPSG codes can be found at [http://spatialreference.org/](http://spatialreference.org/). | Optional | crs=EPSG:4326 |
| geometryType | Type of GeoJSON object to be returned by Featurizer. **Default Value:** linestring **Accepted Values:** linestring, polygon The GeoJSON polygon object is guaranteed to be a closed object, but the linestring object may be open. If the user is in doubt about which geometryType to use, we recommend explicitly using the polygon type, **geometryType=polygon**. Information on the GeoJSON format can be found at [http://geojson.org](http://geojson.org) | Optional | geometryType=polygon |
| operation | Mathematical operator used with threshold to determine which data points are included within the Featurizer line or polygon. **Default Value:** greaterThan **Accepted Values:** lessThan, lessThanOrEqual, greaterThan, greaterThanOrEqual For example, if data records current temperatures in degrees Fahrenheit, the user can retrieve a linestring or polygon containing freezing temperatures by submitting an operation value of “lessThanOrEqual” and a threshold value of 32.0.   | Optional | operation=lessThanOrEqual |
| replacement | Value to be used with Featurizer, when a pixel has no data. **Default Value:** 0.0 Carefully chosen with the operation and threshold parameters in mind, the replacement parameter can cause missing data to be included within or excluded from the polygon or linestring returned by Featurizer. For example, if data records current temperatures in degrees Fahrenheit, and if the user retrieves a polygon or linestring containing freezing temperatures, the user can exclude missing data by setting a replacement value of 40.0 or any other value above the freezing mark. | Optional | replacement=40.0 |
| threshold | Value used with operation to determine which data points are included within the Featurizer linestring or polygon. **Default Value:** 25.0 Float value used with the operation value to determine which data points are included within the polygon or linestring returned by Featurizer. The threshold’s units are determined by the product being evaluated. For the /featurizer/isoband call, this parameter should be two floating point values, separated by a colon, to determine the lower and upper bounds of the values to include in the generated polygon(s), respectively. | Optional | threshold=32.0 For Isoband: threshold=25.0:32.0 |
| stencil (extras/data only) | **Accepted Values:** true, false, or compliment. **Default Value:** false If true then the oceans will be removed. If false, no stenciling is done (same as /tiler/data). If compliment, then the land will be removed. | Optional | stencil=true |
| interpolation (extras/data only) | Which interpolation algorithm to use when providing data at higher LODs than available in a product’s /tiler/info data. **Default Value:** bicubic **Accepted Values:** bicubic \- Custom bicubic interpolation method. typed\_bicubic \- A proprietary use of bicubic interpolation to choose a category. bilinear \- Custom bilinear interpolation. nearest \- Custom nearest neighbor interpolation. influence \- An experimental interpolation method. bicubic2 \- GeoTrellis bicubic implementation. bilinear2 \- GeoTrellis bilinear implementation. nearest2 \- GeoTrellis nearest neighbor implementation. mode2 \- GeoTrellis modal resampling. ptypebicubic \- A proprietary use of bicubic interpolation to choose a category. | Optional | interpolation=bicubic |
| format (isoband only) | Return a response in this format. This may be *json* for GeoJSON, *kml* for KML, *kmz* for a zipped KML, *shp* for a Shapefile or *mvt* for a Mapbox Vector Tile. **Default Value:** json | Optional | format=shp |

### Examples Using Select Parameters for Featurizer

For sample request:  https://api.weather.com/v2/featurizer/tile?product=34:VAR0191200FROM25501heightaboveground\&t=1451606400000\&lod=4\&x=4\&y=6  
&**operation=greaterThanOrEqual**&**threshold=6.0**&**replacement=3.0**&**geometryType=polygon**\&apiKey=yourApiKey

| Goal for Geometry Object Returned by Featurizer | Value for operation | Value for threshold | Value for replacement |
| :---- | :---- | :---- | :---- |
| Product data: temperature in degrees Fahrenheit |  |  |  |
| Goal area with temperatures strictly below freezing, *excluding* missing data | lessThan | 32.0 | 32.0 or higher (ex. 40.0) |
| Goal area with triple-digit temperatures, *including* missing data | greaterThanOrEqual | 100.0 | 100.0 or higher (ex.101.0) |
| Product data: UV index measuring ultraviolet (UV) exposure, where 0-2 is Low, 3-5 is Moderate, 6-7 is High, 8-10 is Very High, and 11 is Extreme |  |  |  |
| Goal area with UV index of “High” or greater, *excluding* missing data | greaterThan | 5.0  | 5.0 or lower (ex. 3.0) |
| **Alternate approach:**  Goal area with UV index of “High” or greater, *excluding* missing data | greaterThanOrEqual | 6.0  | 5.0 or lower (ex. 3.0) |

### Data Elements & Definitions

Note: The table below does not necessarily represent the sort order of the API response. 

| Field Name | Description | Type | Range | Sample |
| :---- | :---- | :---: | :---- | :---- |
| **Tiler Info: v2/tiler/info** |  |  |  |  |
| \<productNumber\> | Object containing a child element for one or more variable ID's associated with the product number | object |  | 303: { tdprob: { }, mhrprob: { }, ... } |
| \<variableID\> | Object containing details on the data that can be retrieved from a given product | object |  | tdprob: { dimensions: \[ \], meta: { } } |
| dimensions | Array of unnamed JSON objects, one for each set of current dimensions for the product number and variable ID, typically timestamps. The dimensions include the ‘t’ and ‘rt’ parameter values for the products requested in the ‘tiler/info’ request. | \[ object \] |  | dimensions: \[ {rt: \[ \], t: \[ \]}, {rt: \[ \], t: \[ \]}, ... \] |
| t | Array of timestamps, in milliseconds, where each is generally the start time for the period covered by the product's data | \[epoch\] |  | rt: \["1471824000000"\] |
| rt | Array of "run time" timestamp, in milliseconds, where each is generally when a forecast was generated | \[epoch\] |  | t: \["1473120000000", "1473033600000", ... \] |
| meta | Object containing metadata for the given product number and variable ID | object |  | meta: { data-href, data-aggregate-href, ... } |
| data-href | URL for the /tiler/data API call | string | Request API URL | data-href: "https://api.weather.com/v2/tiler/data?products=303:tdprob\&rt={rt}\&t={t}\&lod={lod}\&x={x}\&y={y}\&apiKey={apiKey}" |
| data-aggregate-href | URL for the /tiler/data-aggregate API call | string | Request API URL | data-aggregate-href: "https://api.weather.com/v2/tiler/data-aggregate?products=303:tdprob\&rt={rt}\&t={t}\&lod={lod}\&x={x}\&y={y}\&apiKey={apiKey}" |
| cover-href | URL for the /tiler/coverage API call | string | Request API URL | cover-href: "https://api.weather.com/v2/tiler/coverage?products=303:tdprob\&rt={rt}\&t={t}\&apiKey={apiKey}" |
| label | Variable ID | string | Any valid variable ID | label: "tdprob" |
| missingValue | Placeholder, equivalent to NaN (Not a Number) and useful for working with tiler/coverage | string |  | missingValue: "v=-34||v=-35" |
| attributes | Object containing various metadata values, typically from the ingest source | object |  | attributes: {Grib2\_Level\_Type, Grib2\_Parameter, .... } |
| dimensions | Dimensions for the data associated with the product number and variable ID | \[string\] |  | dimensions: \["rt", "t", "geox", "geoy"\] |
| dimension | Details for the entries listed in the dimensions array | object |  | dimension: { rt: {}, t: {}, geox: {}, geoy: {} } |
| \<dimension\> | Details for a single dimension | object |  | rt: {id, primary, type, unit} |
| id | Dimension ID: t for the timestamp of the observation or forecast, rt for the forecast run time, geox for the x-axis location, geoy for the y-axis location, elevation for the geographic height (elsewhere known as the z-axis location), ensemble for the runtime iteration | string | t, rt, geox, geoy, elevation, ensemble | id: "rt" |
| primary | Indicator for the outermost dimension | boolean | true, false | primary: true |
| type | Dimension's data type | string |  | type: "long" |
| unit | Dimension's unit of measurement | string |  | unit: "time in epoch" |
| tilesets | List of tilesets for the data associated with the product number and variable ID | \[string\] | Native, Web Mercator | tilesets: \["Native", "Web Mercator"\] |
| tileset | Details for the entries listed in the tilesets array | object |  | tileset: { Native: {}, Web Mercator: {} } |
| \<tileset\> | Details for a single tileset | object |  | Native: { name, crs, ... } |
| name | Tileset ID, matching an element in the tilesets array and tileset object | string | Native, Web Mercator | name: "Web Mercator" |
| crs | Coordinate Reference System, such as “EPSG:3857” for Web Mercator | string | Any EPSG code or Well Known Text (WKT) | crs: "EPSG:4326" |
| envelope | Bounding box defining the region covered by the tileset | object |  | envelope: { minX, minY, maxX, maxY} |
| minX | Longitude value for the envelope bounding box: degrees or some other measure, depending on the crs value | decimal |  | minX: "-100.0" |
| minY | Latitude value for the envelope bounding box: degrees or some other measure, depending on the crs value | decimal |  | minY: "0.0" |
| maxX | Longitude value for the envelope bounding box: degrees or some other measure, depending on the crs value | decimal |  | maxX: "-5.0" |
| maxY | Latitude value for the envelope bounding box: degrees or some other measure, depending on the crs value | decimal |  | maxY: "50.0" |
| pixel | Object defining the dimensions, in pixels, for the data covered by the tileset | object |  | pixel: { w: 8192, h: 4096 } |
| tile | Object defining the dimensions, in pixels, for a single data tile produced by the tile set | object |  | tile: { w: 256, h: 256 } |
| w | Width for the pixel object or tile object | integer | \>0 | w: 8192 |
| h | Height for the pixel object or tile object | integer | \>0 | h: 4096 |
| tiles | Array of unnamed JSON objects defining the valid set of data tiles at each lod level of detail, for each tileset | \[ object \] |  | tiles: \[ {x, y, width, height, lod}, ... \] |
| x | Zero-based horizontal location of the first tile at a particular lod value, starting at the far left (west) | integer | \>=0 | x: 0 |
| y | Zero-based vertical location of the first tile at a particular lod value, starting at the top (north) | integer | \>=0 | y: 1 |
| width | Number of tiles across the horizontal length of the data set at a particular lod value | integer | \>0 | width: 2 |
| height | Number of tiles down the vertical length of the data set at a particular lod value | integer | \>0 | height: 1 |
| lod | Level of detail, where \-1 indicates the Native Resolution, and 0 and above indicates Web Mercator, where each subsequent LOD value doubles a) the zoom, b) the range of possible x values, and c) the range of possible y values. These ranges are defined below. For any lod value z, where z ≥ 0, 0 ≤ x ≤ (2^z)-1, and 0 ≤ y ≤ (2^z)-1 | integer | \-1 to 9 | lod: 2 |
| ttl | Time to live; the minimum length of time that the data will be available in the system, from its publication to its expected roll-off in seconds | integer | \>0 | ttl: 7200 |
| updateFrequency | Frequency in which new data will be provided in seconds | integer | \>0 | updateFrequency: 900 |

### Appendix: Tiler Info meta=true

By calling the v2/tiler/info API with the optional parameter ‘meta=true’, the details about each requested products native projection and valid Web Mercator tiles are delivered in the response.

| Example | Section | Notes |
| :---- | :---- | ----- |
| **tilesets**:\[      "Native",    "Web Mercator" \], tileset:{      **Native**:{         name: "Native",       crs:"EPSG:4326",       envelope:{            minX:"-39.3695068359375",          minY:"0.005500791594386101",          maxX:"50.6195068359375",          maxY:"89.99449920654297"       },       **pixel**:{            w:8192,          h:8192       },       **tile**:{            w:256,          h:256       },       **tiles**:\[            {               x:0,             y:0,             width:32,             height:32,             lod:-1          }       \]    },    **Web Mercator**:{         name:"Web Mercator",       crs:"EPSG:3857",       **tile**:{            w:256,          h:256       },       **tiles**:\[            {               x:0,             y:0,             width:1,             height:1,             lod:0          },          {               x:0,             y:0,             width:2,             height:1,             lod:1          },          {               x:1,             y:0,             width:2,             height:2,             lod:2          },          {               x:3,             y:0,             width:3,             height:4,             lod:3          },          {               x:6,             y:0,             width:5,             height:8,             lod:4          },          {               x:12,             y:0,             width:9,             height:16,             lod:5          },          {               x:25,             y:0,             width:16,             height:32,             lod:6          },          {               x:50,             y:0,             width:32,             height:64,             lod:7          }       \]    } }, | **tilesets** | This section has two tilesets, one for each projection, “Native” and “Web Mercator.” |
|  | **tileset.Native** | The native projection for this particular incoming data was given in the World Geodetic System developed by the US Department of Defense (officially identified as **EPSG:4326**, as indicated in the **crs** field). The data was limited to an **envelope** in the Northern Hemisphere, encompassing the prime meridian: Longitude, west to east, approximate: 39.4°W to 50.6°E Latitude, south to north, approximate: 0° to 90.0°N (More details about the approximate coverage of Global Radar Tile 2 can be found in **Appendix B**.) |
|  | **tileset.Native.pixel** | The original data was given in a grid of pixels, 8192 pixels on each side, and each pixel contains a single point of data. Not all native-resolution grids will be squares, with the same height and width. |
|  | **tileset.Native.tile** | The original data was split into tiles, each tile containing the standard 256x256 pixels. |
|  | **tileset.Native.tiles** | The original data was divided into tiles of 256x256 pixels, and these tiles were mapped onto a grid, 32 tiles on each side. The grid is assigned a level of detail indicating that the grid is in the native resolution, **lod=-1**. width:  there are 32 tiles, each tile is 256 pixels wide, and 32 x 256 \= 8192, matching the data’s original width height:  there are 32 tiles, each tile is 256 pixels tall, and 32 x 256 \= 8192, matching the data’s original height As with the original grid, the native-resolution tiles will not always form a square, with the same height and width.   The original data will not always fit exactly into a whole number of 256x256 pixels, so there can be tiles with partial data. For example, consider this separate set of **Native** details from the following API call. https://api.weather.com/v2/tiler/info?products=125\&meta=true&**apiKey=yourApiKey**  pixel:{      w:3000,    h:2008 }, tile:{      w:256,    h:256 }, tiles:\[      {         x:0,       y:0,       width:12,       height:8,       lod:-1    } \] The original grid of 3000x2008 pixels is split in tiles of 256x256 pixels, for a grid of 12x8 tiles. width:  there are 12 tiles, each tile is 256 pixels wide, and 12 x 256 \= 3072, slightly more than the data’s original width height:  there are 8 tiles, each tile is 256 pixels tall, and 8 x 256 \= 2048, slightly more than the data’s original height  |
|  | **tileset.Web Mercator** | Taking the standard approach for all products provided through Tiler and Featurizer, the system converts the incoming data from its native projection to the Web Mercator projection (officially identified as **EPSG:3857**, as indicated in the **crs** field). Even when the data is limited to a smaller area \-- as is the case here \--  the tile scheme for this projection encompases almost the entire globe, limited only by the fact that Web Mercator projects both poles at infinity.  Longitude, west to east: 180° to 180° Latitude, south to north, approximate: 85.1°S to 85.1°N Because the Web Mercator tiles are consistent, the **envelope** information is neither needed nor explicitly provided. The **pixel** information is also omitted for the Web Mercator projection, but it can be calculated for each **lod** level of detail. |
|  | **tileset.Web Mercator.tile** | For each **lod** value, the data is split into tiles, each tile containing the standard 256x256 pixels. |
|  | **tileset.Web Mercator.tiles** | The system converts the data from its native projection into the Web Mercator projection at one or more **lod** value, and the set of valid tiles is defined for each level of detail.   For each **lod** value, the set of valid tiles will contain the **envelope** of data from the native projection.  A valid tile may contain partial data \-- and a tile may not always contain data for every timestamp \-- but all data will be limited to valid tiles. For each level of detail, the possible x and y coordinates range between 0 and 2z\-1, where z \= **lod**. Along the x-axis, the first valid tile is found at **x**, and the since the **width** includes this tile, the last tile is at ***x** \+ **width** \- 1*. Along the y-axis, the first valid tile is found at **y**, and the since the **height** includes this tile, the last tile is at ***y** \+ **height** \- 1*. The following table summarizes this particular product’s valid tile locations at each **lod** value for the Web Mercator projection. **lod** Maximum range of **x** and **y** values *0 ≤ **x**,**y** ≤ 2z\-1, where z \= **lod*** Valid **x** Values for This Product *From **x** to **x**\+**width**\-1* Valid **y** Values for This Product *From **y** to **y**\+**height**\-1* 0 0 0 0 1 0 to 1 0 to 1 0 2 0 to 3 1 to 2 0 to 1 3 0 to 7 3 to 5 0 to 3 4 0 to 15 6 to 10 0 to 7 5 0 to 31 12 to 20 0 to 15 6 0 to 63 25 to 40 0 to 31 7 0 to 127 50 to 81 0 to 63  |

### Appendix: Geographical Coverage

Data Tiles \- Native Resolution, and Web Mercator Projection:  
Each product used by Tiler and Featurizer uses data that was originally received in a native projection and then converted into the Web Mercator projection.  Users can typically retrieve data and in either projection. There are more details on the lod parameter and the related parameters x and y in the section on API String Parameters, each projection and each level of detail value is summarized in the table below.

* The **/tiler/data** endpoint, the query string parameters **lod**, **x**, and **y** are used to retrieve individual tiles in both projections.  
* The **/featurizer/tile** endpoints, the query string parameters **lod**, **x**, and **y** are used to retrieve geographic features for individual tiles only in the ***Web Mercator projection***.  
* The **/featurizer/feature** set of endpoints produce geographic features for *all* data in the ***native projection***, without partitioning the data into tiles.

| lod Level of Detail | Tile Size  (pixels) | Length (tiles) \= 2z, where z \= lod and z ≥ 0 | Width (tiles) \= 2z, where z \= lod and z ≥ 0 | Total Number of Tiles \= Length x Width | Total Number of Pixels \= Total Number of Tiles x Tile Size | Approximate Ground Resolution at the Equator  |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Native projection: amount of data and resolution varies with each product |  |  |  |  |  |  |
| \-1 | 256 x 256 | varies | varies | varies | varies | varies |
| Web Mercator projection: number of **lod** values depends on the resolution for the Native projection |  |  |  |  |  |  |
| 0 | 256 x 256 | 1 | 1 | 1 | 65,536 | 160 km / pixel |
| 1 | 256 x 256 | 2 | 2 | 4 | 262,144 | 80 km / pixel |
| 2 | 256 x 256 | 4 | 4 | 16 | 1,048,576 | 40 km / pixel |
| 3 | 256 x 256 | 8 | 8 | 64 | 4,194,304 | 20 km / pixel |
| 4 | 256 x 256 | 16 | 16 | 256 | 16,777,216 | 10 km / pixel |
| 5 | 256 x 256 | 32 | 32 | 1,024 | 67,108,864 | 5 km / pixel |
| 6 | 256 x 256 | 64 | 64 | 4,096 | 268,435,456 | 2 km / pixel |
| 7 | 256 x 256 | 128 | 128 | 16,384 | 1,073,741,824 | 1 km / pixel |
| 8 | 256 x 256 | 256 | 256 | 65,536 | 4,294,967,296 | 0.5 km / pixel |
| 9 | 256 x 256 | 512 | 512 | 262,144 | 17,179,869,184 | 0.25 km / pixel |

### Appendix: Global Radar Tiles

For some sets of radar products, data is partitioned into Global Radar Tiles, where eight adjacent tiles of roughly equal size provide combined coverage for the entire globe. Two of these tiles span the International Date Line, so the data for each of these tiles is partitioned into two products to eliminate any possible ambiguity about the data’s time and date. The following table summarizes the approximate coverage for the Global Radar Tiles, including the split tiles that span the International Date Line. Ranges run west to east and north to south.

| TILE 4 WEST | TILE 1 | TILE 2 | TILE 3 | TILE 4 EAST |
| :---: | :---: | :---: | :---: | :---: |
| *Alaska, North Pacific Ocean* 180° to 130°W 90°N to 0° | *North America, Caribbean* 130°W to 40°W 90°N to 0° | *Europe, Middle East, North Africa* 40°W to 50°E 90°N to 0° | *India, China, Central Asia* 50°E to 140°E 90°N to 0° | *E. Russia, E. Japan, N. Pacific Ocean* 140°E to 180° 90°N to 0° |
| **TILE 8 WEST** | **TILE 5** | **TILE 6** | **TILE 7** | **TILE 8 EAST** |
| *Cook Islands, South Pacific Ocean* 180° to 130°W 0° to 90°S | *South America* 130°W to 40°W 0° to 90°S | *Southern Africa* 40°W to 50°E 0° to 90°S | *Western Australia, Indian Ocean* 50°E to 140°E 0° to 90°S | *Eastern Australia, South Pacific Ocean* 140°E to 180° 0° to 90°S |

### Appendix: Global Satellite Tiles

For some sets of satellite products, data is provided in Global Satellite Tiles, where ten adjacent tiles of various sizes provide coverage for the entire globe between 67°N to 67°S. The following table summarizes the approximate coverage for the Global Satellite Tiles, including the split tiles that span the International Date Line.  Ranges run west to east and north to south.

| TILE 1 | TILE 2 | TILE 3 | TILE 4 | TILE 5 |
| :---: | :---: | :---: | :---: | :---: |
| *North America West (Alaska)* 180° to 125°W 67°N to 13°N | *North America East (CONUS)* 125°W to 39°W 67°N to 13°N | *Europe* 39°W to 60°E 67°N to 13°N | *Asia West* 60°E to 100°E 67°N to 0° | *Asia East* 100°E to 180° 67°N to 0° |
| **TILE 6** | **TILE 7** | **TILE 8** | **TILE 9** | **TILE 10** |
| *Southern Pacific* 180° to 120°W 13°N to 66°S | *South America* 120°W to 20°W 13°N to 66°S | *Africa* 20°W to 60°E 13°N to 66°S | *Indian Ocean (“Western Australia”)* 60°E to 100°E 0° to 66°S | *Australia (“Eastern Australia”)* 100°E to 180° 0° to 66°S |

### Appendix: Aggregation

This endpoint returns **up to four aggregated tiles**. Subsequent tiles are requested by appending comma separated arguments to query arguments. The number of comma separated arguments to each query argument must be equal or the request is invalid. The aggregate tile response is composed of one flag float value optionally followed by a 256x256 float length tile. If the flag float value is 0x00000000 then no tile exists for the combination of comma separated arguments given, and therefore no tile data follows the flag. If the value of negative infinity is given, then a tile follows the flag.

* For example, */tiler/data-aggregate?products={pn1:vid1},{pn2:vid2},{pn:vid3},{pn4:vid4}\&t={t1},{t2},{t3},{t4}\&lod={lod1},{lod2},{lod3},{lod4}\&x={x1},{x2},{x3},{x4}\&y={y1},{y2},{y3},{y4}*  
  * Here, **pn** is the product number, **vid** is the variable ID, and **t** is the “t” (time) dimension; **lod**, **x**, and **y** are the tile coordinates  
* Because the order is mandatory, the user should only aggregate products that use the same dimensions.  
  * The user could aggregate observation products that all use just the **t** dimension.  
  * The user could aggregate forecast products that all use **t** and **rt** dimensions.  
  * The user should **not** aggregate a combination of the two types of products.

Examples  
Adjacent tiles for the same product:

* https://api.weather.com/v2/tiler/data-aggregate?products=300:PrecipIntensity,300:PrecipIntensity\&t=1451606400000,1451606400000\&lod=4,4\&x=3,4\&y=6,6&**apiKey=yourApiKey**

Identical tiles for different products:

* https://api.weather.com/v2/tiler/data-aggregate?products=77:GOESNA1kmVSIRTOAV2,78:GOESNA4kmIR108TOAV2\&t=1451606400000,1451606400000\&lod=4,4\&x=4,4\&y=6,6&**apiKey=yourApiKey**

## Response

The API returns a binary file with the MIME Content-Type “application/octet-stream”,  compressed in response to the following **mandatory** header in the request: “Accept-Encoding: gzip”.

* The response is a gzipped float array, where there are 4 bytes per float in BIG\_ENDIAN order.  
* The results within the response will be ordered to match the comma-delimited list in the request’s parameters.

For each requested tile, the API returns one of the following.

| Condition | Response | Notes |
| :---- | :---- | :---- |
| The requested tile is available | Boundary marker, followed by data “Success” marker: a 4-byte float with the value of *\-Infinity* Data for the requested tile | The value of *\-Infinity* is equivalent to the value returned by *Float.intBitsToFloat(0xff800000)*. Data is sequenced in rows, left to right (west to east), beginning with the top (northmost) row. Since each tile is defined to contain 256 x 256 pixels, and each pixel corresponds to a 4-byte float, the data for each tile will contain 262,144 bytes. |
| The requested tile is **NOT** available | Boundary marker, without data  “Failure” marker: a 4-byte float of 0x00000000 No other data is returned for the requested tile | If this response is for the last requested tile, the data stream will end with this “Failure” boundary marker. Otherwise, the next 4-byte float will be the “Success” or “Failure” boundary marker for the next requested tile. |

Examples

* Two tiles requested, both tiles are successfully returned: **524,296 bytes in the response**  
  * **Tile 1:** 4-byte float of *\-Infinity* followed by 262,144 bytes of data  
  * **Tile 2:** 4-byte float of *\-Infinity* followed by 262,144 bytes of data  
* Two tiles requested, first tile is missing: **262,152 bytes in the response**  
  * **Tile 1:** 4-byte float with the value 0x00000000  
  * **Tile 2:** 4-byte float of *\-Infinity* followed by 262,144 bytes of data  
* Two tiles requested, both tiles are missing: **8 bytes in the response**  
  * **Tile 1:** 4-byte float with the value 0x00000000  
  * **Tile 2:** 4-byte float with the value 0x00000000

### Document Revision History

| Revision | Date | Notes |
| :---- | :---- | :---- |
| 1.0 | Dec 7, 2018 | Initial versioned document; addition of Document Revision History |
| 2.0 | Jun 7, 2022 | Added information for /tiler/byte, /tiler/coverage, /tiler/extras/data, and /featurizer/isoband endpoints |

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,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>