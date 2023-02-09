import random
import time
import math
from io import BytesIO

import requests

from PIL import Image

import osmnx as ox  # https://github.com/gboeing/osmnx
import geopandas as gpd  # https://geopandas.org/
import mercantile as mc  # https://github.com/mapbox/mercantile

import rasterio.features
import rasterio.transform

BING_API_URL = "https://dev.virtualearth.net/REST/v1/Imagery/Metadata/{imagerySet}/{centerPoint}?zl={zoomLevel}&key={BING_KEY}"


# https://social.msdn.microsoft.com/Forums/en-US/5454d549-5eeb-43a5-b188-63121d3f0cc1/how-to-set-zoomlevel-for-particular-altitude?forum=bingmaps
def altitude2zoomlevel(altitudeMeters):
    return int(19 - math.log(altitudeMeters/1000 * 5.508, 2))


# https://wiki.openstreetmap.org/wiki/Zoom_levels
def h_dist(latitudeDegrees, altitudeMeters=None, zoomLevel=None):
    '''The horizontal distance represented by each square tile, 
    measured along the parallel at a given latitude'''
    C = 2*math.pi*6378137
    if altitudeMeters:
        zoomlevel = altitude2zoomlevel(altitudeMeters)
        return C * math.cos(latitudeDegrees*math.pi/180) / 2**zoomlevel
    elif zoomLevel:
        return C * math.cos(latitudeDegrees*math.pi/180) / 2**zoomlevel
    else:
        raise RuntimeError("Wrong arguments!")


# https://learn.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
def tile2quad(x, y, z):
    quad = ''
    for i in range(z, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if ((x & mask) != 0):
            digit += 1
        if ((y & mask) != 0):
            digit += 2
        quad = quad + str(digit)
    return quad


def getAerialImage(lat, lon, zoomLevel, bing_key, bing_api_url=BING_API_URL):
    response = requests.get(bing_api_url.format(imagerySet="Aerial", 
                                                centerPoint=f"{lat},{lon}",
                                                zoomLevel=zoomLevel,
                                                BING_KEY=bing_key)).json()
    if response.get('errorDetails', False):
        raise RuntimeError(",".join(response['errorDetails']))
    else:
        resources = response['resourceSets'][0]['resources'][0]
        imageUrl = resources['imageUrl']
        imgStr = requests.get(imageUrl, allow_redirects=True)
        if imgStr.status_code == 200:
            return Image.open(BytesIO(imgStr.content))
        else:
            raise RuntimeError(imgStr)


def getTiles(west, south, east, north, zoomLevel):
    assert zoomLevel <= 20, "zoomLevel>20!"
    lst_tile = mc.bounding_tile(west, south, east, north)
    try:
        res = mc.children(lst_tile, zoom=zoomLevel)
    except mc.InvalidZoomError as err:
        raise mc.InvalidZoomError(lst_tile, err.args[0])

    return res


def getMask(west, south, east, north, imgSize, tags={"building": True}):
    west, south, east, north = mc.bounds(mc.bounding_tile(west, south, east, north))
    maskShapely = gpd.clip(ox.geometries_from_bbox(north, south, east, west, tags),
                           (west, south, east, north)).geometry.values
    img = rasterio.features.rasterize(maskShapely, out_shape=imgSize, fill=0,
                                      transform=rasterio.transform.from_bounds(west, south, east, north, *imgSize),
                                      dtype='uint8')
    return Image.fromarray(img*255)


def getFusedImg(west, south, east, north, zoomLevel,
                bing_key, maxTiles=32, minT=0.05):
    tiles = getTiles(west, south, east, north, zoomLevel)
    assert len(tiles) <= maxTiles, f"You are trying to ask for more than {maxTiles} tiles, are you sure?"
    size = int(math.sqrt(len(tiles)))
    x, y, z = tiles[0]
    totalSize = size*256  # images (tiles) from Bing are 256x256
    finaImg = Image.new('RGB', (totalSize, totalSize))
    for i in range(size):
        for j in range(size):
            tmpLngLat = mc.ul(mc.Tile(x+i, y+j, z))
            tmpImg = getAerialImage(tmpLngLat.lat, tmpLngLat.lng, z, bing_key)
            time.sleep(minT+random.random()*minT)
            finaImg.paste(tmpImg, (256*i, 256*j))

    return finaImg
