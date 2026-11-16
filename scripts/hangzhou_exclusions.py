"""Canonical OSM IDs for candidate integration; no implicit way/relation guesses."""
import re

def normalized_exclusion_ids(raw_ids,spec):
 refs=[]
 def sources(value):
  if isinstance(value,dict):
   for key,item in value.items():
    namespace={'osmWayId':'way','osmRelationId':'relation'}.get(key)
    if namespace and isinstance(item,int) and not isinstance(item,bool):
     ref=namespace+'/'+str(item)
     if ref not in refs:refs.append(ref)
    if key not in ('baseBuildingIdsToExclude','sourceSpecExclusionIds'):sources(item)
  elif isinstance(value,list):
   for item in value:sources(item)
  elif isinstance(value,str) and re.fullmatch(r'(way|relation)/\d+',value) and value not in refs:refs.append(value)
 sources(spec)
 # A qualified exclusion in the frozen spec is an explicit declaration, even
 # when the object uses a campus footprint or estimated bridge above it.
 # Actual source existence/coverage is checked by the integration inventory.
 for ref in spec.get('baseBuildingIdsToExclude',[]):
  if isinstance(ref,str) and re.fullmatch(r'(way|relation)/\d+',ref) and ref not in refs:refs.append(ref)
 result=[]
 for value in raw_ids:
  text=str(value)
  if re.fullmatch(r'(way|relation)/\d+',text):key=text
  elif text.isdigit():
   matches=[ref for ref in refs if ref.split('/')[1]==text]
   if len(matches)!=1:raise ValueError('Unqualified OSM exclusion needs one explicit source feature: '+text)
   key=matches[0]
  else:raise ValueError('Invalid OSM building exclusion '+text)
  if key not in refs:raise ValueError('Exclusion is outside the declared source features: '+key)
  if key not in result:result.append(key)
 return result
