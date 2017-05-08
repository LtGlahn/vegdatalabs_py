# -*- coding: utf-8 -*-
"""
Created on Fri May  5 23:00:26 2017

@author: jan
"""

import requests
import copy
import pandas as pd

s = requests.Session()
s.headers = {  'accept' : 'application/vnd.vegvesen.nvdb-v2+json', 
                            'X-Client' : 'nvdbapi.py',
                            'X-Kontaktperson' : 'jan.kristian.jensen@vegvesen.no' }



def hentstatistikk( objektid, params ): 
    nvdbapi = 'https://www.vegvesen.no/nvdb/api/v2' 
    
    url = '/'.join( [ nvdbapi, 'vegobjekter', str(objektid), 'statistikk' ])
    r = s.get( url, params = params )
    # print( r.url ) 
    return r.json()


def lagulykkestat( terskelverdier): 

    # Filter til NVDB api 
    vegref = { 'vegreferanse' : 'E,R,F' }
    ulfilter = copy.deepcopy( vegref)
    aadtfilter = copy.deepcopy( vegref)
    data = []
    for k in range(1, len( terskelverdier)): 
        adt_lo = terskelverdier[k-1]
        adt_hi = terskelverdier[k]
        
        ulfilter = copy.deepcopy( vegref)
        
        ulfilter['overlapp'] = '540(4623>=' + str(adt_lo) + \
                                ' AND 4623<' + str(adt_hi) + ')'
        
        aadtfilter['egenskap'] = '(4623>=' + str(adt_lo) + \
                                ' AND 4623<' + str(adt_hi) + ')'
        
        ul_alle = hentstatistikk( 570, ulfilter)
        aadt = hentstatistikk( 540, aadtfilter)
        
        ulfilter['egenskap'] = '5074=6427' # Alv.skadegrad=drept
        ul_drept = hentstatistikk(570, ulfilter)
    
        ulfilter['egenskap'] = '5074=6428' # Meget alvorlig skadd
        ul_mas = hentstatistikk(570, ulfilter)
    
        ulfilter['egenskap'] = '5074=6429' # Alvorlig skadd
        ul_as = hentstatistikk(570, ulfilter)
        
        ulfilter['egenskap'] = '5074=6430' # Lettere skadd
        ul_ls = hentstatistikk(570, ulfilter)
    
        #print(ul)
        # print( aadt )
        ufreq = ul_drept['antall'] / aadt['strekningslengde']
        enrad = (adt_lo, adt_hi, aadt['strekningslengde'], ul_alle['antall'], 
                 ul_drept['antall'], ul_mas['antall'], ul_as['antall'], ul_ls['antall'] )
        
        data.append(enrad)
    
    labels = ['aadt_lo', 'aadt_hi', 'lengde', 'ul_tot', 'ul_drept', 'ul_mas', 'ul_as', 'ul_ls']    
    df = pd.DataFrame.from_records( data, columns=labels)
    return df


### Script-delen
terskelverdier = [ 150, 250, 400, 600, 900, 1380, 2100, 3500, 6865, 1e5]

df_bearingPt = lagulykkestat(terskelverdier)

