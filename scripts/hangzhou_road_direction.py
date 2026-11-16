"""OSM way direction for the existing one-way navigation interface."""
def road_direction(tags):
    value=tags.get('oneway')
    if value in ('yes','1','true'):return True,False,'explicit-forward'
    if value=='-1':return True,True,'explicit-reverse'
    if value in ('no','0','false'):return False,False,'explicit-two-way'
    if value not in (None,''):raise ValueError('Unsupported source direction: '+value)
    if tags.get('junction')=='roundabout' or tags.get('highway')=='motorway':return True,False,'implied-by-source-type'
    return False,False,'no-oneway-restriction-recorded'
