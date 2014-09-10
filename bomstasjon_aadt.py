# -*- coding: utf-8 -*-

import nvdb
import json
from shapely.wkt import loads
from shapely.geometry import mapping
import pdb
import traceback


def hentbomstasjon( sokeObjekt='', lokasjon = '', params = ''):
    """
    Henter alle bomstasjoner fra NVDB api'et.
    Burde vært datakatalog-drevet, men er det ikke.
    Koden kan altså knekke hvis fremtidige revisjoner av datakatalogen endrer
    på bomstasjonenes egenskaper.

    Funker mot versjon 1.93. Sjekk gjeldende versjon her
    http://www.vegvesen.no/Fag/Teknologi/Nasjonal+vegdatabank/Datakatalogen
    evt programatisk mot api'et  https://www.vegvesen.no/nvdb/api/datakatalog
    """

    if not sokeObjekt:
        sokeObjekt =  {'objektTyper': [ {'id': 45, 'antall': 250} ] }

    if not params:
        params = { 'geometriType' : 'WGS84' }

    data = nvdb.query_search( sokeObjekt, lokasjon = lokasjon, params = params)

    # newdata er en liste med lister - en per bomstasjon pluss header
    newdata, bomGeoJson, aadtGeojson = getRelevantData( data)
    newdata.reverse() # Snur listen to ganger for å starte med header
    newdata.append( [ 'bnavn1', 'tliten', 'tstor, vegnummer', 'lat', 'lon',
                            'harAp', 'apBeskr', 'kommunenr', 'bomstasjonId',
                            'aadtTotal', 'aadtLGV', 'aadtYear', 'aadtId'
                            ] )
    newdata.reverse()

    csvfil = 'bomstasjoner.csv'
    nvdb.csv_skriv( csvfil, newdata)

    # Skriver geojson til fil
    with open('bomGeoJson.json', 'wb') as fb:
        json.dump(bomGeoJson, fb)

    # Skriver geojson til fil
    with open('aadtGeoJson.json', 'wb') as fa:
        json.dump(bomGeoJson, fa)


def getRelevantData( data):
    """Wrapper rundt nvdb.py sine objektorienterte funksjoner for manipulering
    av data fra NVDB api.
    Trivielt å utvide denne listen med nye egenskaper ut fra datakatalog
    """

    newdata = []
    bomsGeoJson = { "type": "FeatureCollection", "features": [] }
    aadtGeoJson = { "type": "FeatureCollection", "features": [] }
    count = 0
    miscount = 0
    miscountAadt = 0
#    vegobjekter = data.objekter()

    for bomstasjon in data.vegObjekter:
#         vegObjekt = nvdb.Objekt(bomstasjon)

        try:
            bnavn1 = bomstasjon.egenskap( 1078 ) # Navn
            tliten = bomstasjon.egenskap( 1820 ) # Takst
            tstor  = bomstasjon.egenskap(  1819 ) # Takst
            harAp, apBeskr = abonnementstype( bomstasjon )
            bomstasjonId = bomstasjon.id

            # Henter lokasjonsdata
            lokasjon = bomstasjon.lokasjon()
            kommunenr = '{:0>4d}'.format(lokasjon['kommune']['nummer'])
            lon, lat = hentXYpoint( lokasjon['geometriWgs84'] )
            vegnummer = hentvegnr( lokasjon['vegReferanser'] )

            success = True

        except Exception, e:
            print "========================================"
            print "Klarte ikke dekode dette objektet\n", e
            # print json.dumps( b, indent=4)
            success = False
            miscount += 1
            traceback.print_exc()

        if success:
            try:
                trafikkmengde = hentAadt( bomstasjon)
                # if trafikkmengde.antall > 1:
                if not sjekkAntall(trafikkmengde):
                    # pdb.set_trace()
                    raise Exception, "Fant mer enn 1 trafikkmengde-forekomst"

                aadtTotal = trafikkmengde.vegObjekter[0].egenskap( 4623)
                aadtLGV  = trafikkmengde.vegObjekter[0].egenskap( 4624)
                aadtYear = trafikkmengde.vegObjekter[0].egenskap( 4621)
                aadtId = trafikkmengde.vegObjekter[0].id
                aadtSuccess = True

            except Exception, e:
                print "Klarte ikke hente trafikkdata for bomstasjon", \
                        bomstasjonId, " :", bnavn1, vegnummer, "kommune:", kommunenr
                # traceback.print_exc()
                aadtTotal = '-9999'
                aadtTotal = '-9999'
                aadtLGV = '-9999'
                aadtYear = '-9999'
                aadtId = '-9999'
                miscountAadt += 1
                aadtSuccess = False

            if aadtSuccess:
                aadtGeoJson['features'].append( makeGeoJson( trafikkmengde.vegObjekter[0],
                 { 'bnavn1' : bnavn1, 'tliten' : tliten, 'tstor' : tstor,
                    'vegnummer' : vegnummer, 'harAp' : harAp,
                    'apBeskr' : apBeskr, 'kommunenr': kommunenr,
                    'bomstasjonId': bomstasjonId, 'aadtTotal': aadtTotal,
                    'aadtLGV': aadtLGV, 'aadtYear': aadtYear,
                    'aadtId': aadtId
                }))

        if success:
            newdata.append( [ bnavn1, tliten, tstor, vegnummer, lat, lon,
                            harAp, apBeskr, kommunenr, bomstasjonId,
                            aadtTotal, aadtLGV, aadtYear, aadtId
                            ] )
            count += 1
            bomsGeoJson['features'].append( makeGeoJson( bomstasjon,
                 { 'bnavn1' : bnavn1, 'tliten' : tliten, 'tstor' : tstor,
                    'vegnummer' : vegnummer, 'harAp' : harAp,
                    'apBeskr' : apBeskr, 'kommunenr': kommunenr,
                    'bomstasjonId': bomstasjonId, 'aadtTotal': aadtTotal,
                    'aadtLGV': aadtLGV, 'aadtYear': aadtYear,
                    'aadtId': aadtId
                }))

    print "Hentet ", count, "bomstasjoner - ", miscount, "feilet", " og ", \
            miscountAadt, " mangler Trafikkmengde"

    return (newdata, bomsGeoJson, aadtGeoJson)

def hentAadt( vegObjekt):

    objektTyper =  [ {'id': 540, 'antall': 2500} ]
    lokasjon =  { 'veglenker': vegObjekt.veglenker() }
    params = { 'geometriType' : 'WGS84' }

    trafikkmengde = nvdb.query_search( objektTyper, lokasjon = lokasjon, params = params)

    return trafikkmengde

def sjekkAntall( sokeresultat):
    # Bug i NVDB API (per 10.9)? Kall som er garantert å gi kun en forekomst
    # gir nå dubletter...?
    if sokeresultat.antall == 1:
        return True
    elif sokeresultat.antall == 2 and sokeresultat.vegObjekter[0].id == sokeresultat.vegObjekter[1].id:
        return True

    return False

def abonnementstype( nvdbObj):
        btype = nvdbObj.egenskap( 9390)
        utgAp  = nvdbObj.egenskap( 8405)

        if btype:
            apBeskr = btype
            if btype == "Kun manuell":
                harAp = 'Nei'
            else:
                harAp = 'Ja'

        elif utgAp:
            if utgAp == u'Utgår_Autopass':
                harAp = 'Ja'
                apBeskr = 'Har autopass'
            elif utgAp == u'Utgår_Lokalt abonnement':
                harAp = 'Nei'
                apBeskr = 'Lokalt abonnement'
            elif utgAp == u'Utgår_Ikke abonnement':
                harAp = 'Nei'
                apBeskr = 'Ikke abonnement'
            else:
                harAp = '???'
                apBeskr = '??? FANT IKKE DATA'

        else:
            harAp = 'Ja'
            apBeskr = 'Har autopass'

        return (harAp, apBeskr)


def hentXYpoint( coordstr):
    """Henter X-Y koordinater fra streng.
    Bomstasjoner er punktobjekt med ett sett koordinater.
    Hvis du gjenbruker kode på strekningsobjekt må du modifisere
    slik at du håndterer en liste med koordinater.
    """

    # loads hentet fra shapely.wkt  -modul
    p = loads( coordstr)
    return( '{:.5f}'.format(p.x), '{:.5f}'.format(p.y) )

def makeGeoJson( vegObjekt, properties ):

    lokasjon = vegObjekt.lokasjon()

    p = loads( lokasjon['geometriWgs84'])

    geo = {
              "type": "Feature",
              "geometry": mapping(p),
              "properties": properties
        }

    return geo



def hentvegnr( vegreferanser):
    """
    Henter et vegnummer ut fra det første vegreferanse-objektet.
    Greit nok for punktobjekt - men ikke godt nok for objekter med lang
    utstrekning, de kan potensielt ha flere enn 1 vegreferanse
    """

    vegnr = str( vegreferanser[0]['kategori']) + \
                    str( vegreferanser[0]['status']).lower() + \
                    str(vegreferanser[0]['nummer'])
    return vegnr



if __name__=="__main__":
    hentbomstasjon( [{'id': 45, 'antall': 1000}] )


#    data = hentbomstasjon( sokeobjekt=[{'id': 45, 'antall': 250}],
#        lokasjon= {"bbox":"-37501.587503176,6563593.7896875,-33723.329946661,6566647.0874608"}
#        )
#
#    if data:
#        json.dumps(data, indent=4, separators=(',', ': '))
