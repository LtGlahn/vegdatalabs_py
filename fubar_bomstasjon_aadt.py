# -*- coding: utf-8 -*-

import nvdb
import json
from shapely.wkt import loads
import csv
import pdb


def hentbomstasjon( sokeObjekt='', lokasjon = ''):
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
        sokeObjekt =  [ {'id': 45, 'antall': 250} ]

    data = nvdb.query_search( sokeObjekt, lokasjon = lokasjon, geometriType = 'WGS84')

    # newdata er en liste med lister - en per bomstasjon pluss header
    newdata = getRelevantData( data)
    newdata.reverse() # Snur listen to ganger for å starte med header
    newdata.append(  [ 'Navn', 'Takst liten bil', 'Takst stor bil',  'Vegnummer',
                'Lat', 'Long:', 'Autopass', 'Autopass-beskrivelse',
                            'Kommunenr'
                ] )
    newdata.reverse()

    csvfil = 'bomstasjoner.csv'
    skrivcsv(newdata,  csvfil)

    # return newdata

def getRelevantData( data):
    """Wrapper rundt funksjonen finnEgenskapVerdi
    Trivielt å utvide denne listen med nye egenskaper ut fra datakatalog
    """

    newdata = []
    count = 0
    miscount = 0
    for b in data['resultater'][0]['vegObjekter']:
        try:
            bnavn1 = finnEgenskapVerdi( b['egenskaper'], 1078, 'verdi') # Navn
            tliten = finnEgenskapVerdi( b['egenskaper'], 1820, 'verdi') # Takst
            tstor  = finnEgenskapVerdi( b['egenskaper'], 1819, 'verdi') # Takst
            harAp, apBeskr = abonnementstype( b['egenskaper'])

            # Henter lokasjon
            kommunenr = '{:0>4d}'.format(b['lokasjon']['kommune']['nummer'])
            lon, lat = hentXYpoint( b['lokasjon']['geometriWgs84'] )
            vegnummer = hentvegnr( b['lokasjon']['vegReferanser'] )
            test = hentAadt( b['lokasjon'])
            success = True

        except Exception:
            print "========================================"
            print "Klarte ikke dekode dette objektet"
            print json.dumps( b, indent=4)
            success = False
            miscount += 1

        if success:
            newdata.append( [ bnavn1, tliten, tstor, vegnummer, lat, lon,
                            harAp, apBeskr, kommunenr
                            ] )
            count += 1

    print "Hentet ", count, "bomstasjoner - ", miscount, "feilet"
    return newdata

def hentAadt( lokasjon):
    veglenkeID  = lokasjon['veglenker'][0]['id']
    veglenkeFra = lokasjon['veglenker'][0]['fra']
    veglenkeTil = lokasjon['veglenker'][0]['til']



    return veglenkeID

def abonnementstype( egenskapsliste):
        btype = finnEgenskapVerdi( egenskapsliste, 9390, 'verdi')
        utgAp  = finnEgenskapVerdi( egenskapsliste, 8405, 'verdi')

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


def finnEgenskapVerdi( egenskapliste, id, attributt ):
    """Soeker gjennom egenskapsliste etter oppgitt ID og attributt.
    ID er unik, derfor er vi happy med å returnere første match.
    """
    for eg in egenskapliste:
        if eg['id'] == id and attributt in eg:
            return eg[attributt]

    # Hvis vi kommer hit har vi feilet
    return False

def hentXYpoint( coordstr):
    """Henter X-Y koordinater fra streng.
    Bomstasjoner er punktobjekt med ett sett koordinater.
    Hvis du gjenbruker kode på strekningsobjekt må du modifisere
    slik at du håndterer en liste med koordinater.
    """

    # loads hentet fra shapely.wkt  -modul
    p = loads( coordstr)
    return( '{:.5f}'.format(p.x), '{:.5f}'.format(p.y) )

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



def skrivcsv( data, filename):
    """
    Skriver resultatene til CSV-fil. Men unicode-v.s.-UTF-8 problematikken
    er ikke støttet på noen god måte i CSV-biblioteket. Har derfor et hack
    for å konvertere alle unicode-strenger (typisk u'streng' - i JSON
    objektet!) til UTF-8.
    """

    # Unicode med CSV er skikkelig PLAGE! Hack for å konvertere alle felter
    # til utf-8...
    for index1, row in enumerate(data):
        for index2, cell in enumerate(row):
            if isinstance(cell, unicode):
                data[index1][index2] = cell.encode('utf-8')

    with open(filename, 'wb') as fp:
        fp.write(u'\ufeff'.encode('utf8')) # BOM (optional...
                                            # Excel needs it to open UTF-8
        a = csv.writer(fp, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL )
        a.writerows(data)



if __name__=="__main__":
    hentbomstasjon( [{'id': 45, 'antall': 1000}] )


#    data = hentbomstasjon( sokeobjekt=[{'id': 45, 'antall': 250}],
#        lokasjon= {"bbox":"-37501.587503176,6563593.7896875,-33723.329946661,6566647.0874608"}
#        )
#
#    if data:
#        json.dumps(data, indent=4, separators=(',', ': '))
