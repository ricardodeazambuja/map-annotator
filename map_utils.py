import math

# https://social.msdn.microsoft.com/Forums/en-US/5454d549-5eeb-43a5-b188-63121d3f0cc1/how-to-set-zoomlevel-for-particular-altitude?forum=bingmaps
def altitude2zoomlevel(altitudeMeters):
    return int(19 - math.log(altitudeMeters/1000 * 5.508, 2))

# https://wiki.openstreetmap.org/wiki/Zoom_levels
def h_dist(latitudeDegrees, altitudeMeters):
    '''The horizontal distance represented by each square tile, 
    measured along the parallel at a given latitude'''
    C = 2*math.pi*6378137
    zoomlevel = altitude2zoomlevel(altitudeMeters)
    return C * math.cos(latitudeDegrees*math.pi/180) / 2**zoomlevel


# https://learn.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
def tile2quad(x, y, z):
    quad = ''
    for i in range(z,0,-1):
        digit = 0
        mask = 1 << (i - 1)
        if ((x & mask) != 0):
            digit += 1
        if ((y & mask) != 0):
            digit += 2
        quad = quad + str(digit);
    return quad