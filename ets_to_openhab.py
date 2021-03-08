import csv
import os.path

def data_of_name(data, name):
    for x in data:
        if x['Group name'] == name:
            return x
    return None

openhabdir = '../../openhab'
csvfile = open('../ets_gruppenadressen.csv', newline='', encoding='cp1252')

reader = csv.DictReader(csvfile, delimiter='\t')

house = {}
export_to_influx = []
used_addresses = []

for row in reader:
    print(row)
    # check if floor:
    if row['Address'].endswith('/-/-'):
        row['rooms'] = {}
        house[row['Address'].split('/')[0]] = row
    # check if room
    elif row['Address'].endswith('/-'):
        splitter = row['Address'].split('/')
        row['Addresses'] = []
        house[splitter[0]]['rooms'][splitter[1]] = row
    # normal group address
    else:
        splitter = row['Address'].split('/')
        house[splitter[0]]['rooms'][splitter[1]]['Addresses'].append(row)

items = ''
sitemap = ''
things = ''
semantic_things = ''
selections = ''
semantic_cnt = 0
fensterkontakte = []
cnt = 0
for floorNr in house.keys():
    items += f"Group           map{floorNr}                     \"{house[floorNr]['Group name']}\"             (Home)                    [\"Location\"]\n"
    sitemap += f"Frame label=\"{house[floorNr]['Group name']}\" {{\n"
    for roomNr in house[floorNr]['rooms'].keys():
        roomName = house[floorNr]['rooms'][roomNr]['Group name']
        items += f"Group           map{floorNr}_{roomNr}                     \"{roomName}\"             (map{floorNr})                    [\"Location\"]\n"
        sitemap += f"     Group item=map{floorNr}_{roomNr}\n"

        addresses = house[floorNr]['rooms'][roomNr]['Addresses']

        for i in range(len(addresses)):

            used = False

            address = house[floorNr]['rooms'][roomNr]['Addresses'][i]
            lovely_name = ' '.join(address['Group name'].replace(house[floorNr]['Group name'],'').replace(house[floorNr]['rooms'][roomNr]['Group name'],'').split())

            #print(f"--- processing: {lovely_name}")
            #print(address)

            if 'IGNORE' in address.keys():
                continue

            item_name = f"i_{cnt}_{house[floorNr]['Group name']}_{house[floorNr]['rooms'][roomNr]['Group name']}_{lovely_name}".replace('/','_').replace(' ','_')
            item_name = item_name.replace('ü','ue').replace('ä','ae').replace('ß','ss')
            
            semantic = False
            # temperatur
            if address['DatapointType'] == 'DPST-9-1':
                used = True
                thing_type = 'number'
                thigs_group_adresses = address['Address']

                item_type = 'Number'
                item_Description = f"{lovely_name} [%.1f °C]"
                item_icon = 'temperature'
                semantic = True
                #things += f"Type number        : {item_name}        \"{address['Group name']}\" @ {roomName}       [ ga=\"{address['Address']}\" ]\n"
                #items += f"Number        {item_name}         \"{lovely_name} [%.1f °C]\"                <temperature>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"



            # umschalten (licht, steckdosen)
            if address['DatapointType'] == 'DPST-1-1':
                if not address['Group name'].endswith(' Status'):
                    status = data_of_name(addresses, address['Group name'] + ' Status')
                    if status:
                        used = True
                        used_addresses.append(status['Address'])
                        typ = 'light'
                        if 'Steckdose' in address['Group name']:
                            typ = 'poweroutlet'
                        lovely_name = ' '.join(lovely_name.replace('Licht','').replace('Steckdose','').split())
                        things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}+<{status['Address']}\" ]\n"
                        items += f"Switch        {item_name}         \"{lovely_name}\"               <{typ}>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    
            # dimmer
            if address['Group name'].endswith('Dimmen absolut'):
                basename = address['Group name'].replace('Dimmen absolut','')
                schalten = data_of_name(addresses, basename + 'Schalten')
                dimmen_relativ = data_of_name(addresses, basename + 'Dimmen relativ')
                schalten_status = data_of_name(addresses, basename + 'Status Ein/Aus')
                dimmwert_status = data_of_name(addresses, basename + 'Status Dimmwert')
                if dimmen_relativ and schalten and schalten_status and dimmwert_status:
                    used = True
                    used_addresses.append(dimmen_relativ['Address'])
                    used_addresses.append(schalten['Address'])
                    used_addresses.append(schalten_status['Address'])
                    used_addresses.append(dimmwert_status['Address'])

                    lovely_name = ' '.join(lovely_name.replace('Dimmen','').replace('Dimmer','').replace('absolut','').replace('Licht','').split())
                    things += f"Type dimmer        : {item_name}        \"{address['Group name'].replace('absolut','')}\"        "
                    things += f"[ position=\"{address['Address']}+<{dimmwert_status['Address']}\"]\n"
                    items += f"Dimmer        {item_name}         \"{lovely_name} [%d %%]\"               <light>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # rollos / jalousien
            if address['DatapointType'] == 'DPST-1-8':
                if 'tatus' in address['Group name']: # ignore status
                    continue
                if 'aktuell' in address['Group name']: # ignore status
                    continue
                basename = address['Group name'].replace('Auf/Ab','')

                fahren_auf_ab = data_of_name(addresses, basename + 'Auf/Ab')
                fahren_stop = data_of_name(addresses, basename + 'Lamellenverstellung/Stop')
                if not fahren_stop:
                    fahren_stop = data_of_name(addresses, basename + 'Stop')
                if not fahren_stop:
                    fahren_stop = data_of_name(addresses, basename + 'Stopp')
                absolute_position = data_of_name(addresses, basename + 'absolute Position')
                absolute_position_status = data_of_name(addresses, basename + 'Status')

                #Status Richtung nicht in verwendung durch openhab
                drop = data_of_name(addresses, basename + 'Status Richtung')
                if drop:
                    used_addresses.append(drop['Address'])

                lovely_name = lovely_name.replace('Auf/Ab','')
                
                if fahren_auf_ab and fahren_stop and absolute_position and absolute_position_status:
                    used = True
                    used_addresses.append(fahren_auf_ab['Address'])
                    used_addresses.append(fahren_stop['Address'])
                    used_addresses.append(absolute_position['Address'])
                    used_addresses.append(absolute_position_status['Address'])

                    things += f"Type rollershutter : {item_name} [ upDown=\"{fahren_auf_ab['Address']}\", stopMove=\"{fahren_stop['Address']}\", position=\"{absolute_position['Address']}+<{absolute_position_status['Address']}\" ]\n"
                    items += f"Rollershutter        {item_name}         \"{lovely_name} [%d %%]\"    (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                else:
                    print(f"incomplete rollershutter: {basename}")
            
            # Fensterkontakte
            if 'Fensterkontakt' in address['Group name']:
                used = True
                lovely_name = ' '.join(lovely_name.replace('Fensterkontakt','').split())
                #things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\" ]\n"
                #items += f"Switch        {item_name}         \"{lovely_name}\"               <contact>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                things += f"Type contact        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\"]\n"
                items += f"Contact        {item_name}         \"{lovely_name}\"               <contact>  (map{floorNr}_{roomNr})       {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                fensterkontakte.append({'item_name': item_name, 'name': address['Group name']})

            # Arbeit (wh)
            if address['DatapointType'] == 'DPST-13-10':
                used = True
                lovely_name = ' '.join(lovely_name.replace('Leistung','').split())
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"13.010:{address['Address']}\" ]\n"
                items += f"Number        {item_name}         \"{lovely_name} [%.1f Wh]\"                <batterylevel>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
        
            # Leistung (W)
            if address['DatapointType'] == 'DPST-14-56':
                used = True
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"14.056:{address['Address']}\" ]\n"
                items += f"Number        {item_name}         \"{lovely_name} [%.1f Watt]\"  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # Strom
            if address['DatapointType'] == 'DPST-7-12':
                used = True
                lovely_name = ' '.join(lovely_name.replace('Strom','').replace('aktuell','').split())
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"7.012:{address['Address']}\" ]\n"
                items += f"Number        {item_name}         \"{lovely_name} [%.1f mA]\"                <batterylevel>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # Lux
            if address['DatapointType'] == 'DPST-9-4':
                used = True
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"9.004:{address['Address']}\" ]\n"
                items += f"Number        {item_name}         \"{lovely_name} [%.1f LUX]\"                <sun>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
            
            # Geschwindigkeit m/s
            if address['DatapointType'] == 'DPST-9-5':
                used = True
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"9.005:{address['Address']}\" ]\n"
                items += f"Number        {item_name}         \"{lovely_name} [%.1f m/s]\"                <wind>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # Präsenz
            if address['DatapointType'] == 'DPST-1-1':
                if 'Präsenz' in address['Group name']:
                    used = True
                    things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\" ]\n"
                    items += f"Switch        {item_name}         \"{lovely_name}\"               <parents_2_3>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # Szene
            if address['DatapointType'] == 'DPST-17-1':
                print(address)
                used = True
                mappings=''
                #if 'mappings' in address['Description']:
                #    #TODO: split other values
                #    mappings = address['Description']
                things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ga=\"17.001:{address['Address']}\"]\n"
                
                if 'mappings' in address['Description']:
                    #TODO: split other values
                    mapfile = f"gen_{item_name}.map"
                    mappings = address['Description'].replace("'",'"')
                    #TODO: move this
                    selections += f"Selection item={item_name} label=\"{lovely_name}\"  {mappings}\n"
                    items += f"Number        {item_name}         \"{lovely_name} [MAP({mapfile}):%s]\"               <movecontrol>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    mapfile_content = mappings.replace('"','').replace(',','\n').replace('mappings=[','').replace(']','').replace(' ','')
                    mapfile_content += '\n' + mapfile_content.replace('=','.0=') + '\n-=unknown'
                    open(f"{openhabdir}/transform/{mapfile}",'w').write(mapfile_content)
                else:
                    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <movecontrol>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                
                
                    
            # Szenensteuerung
            #if address['DatapointType'] == 'DPST-18-1':
            #    print(address)
            #    used = True
            #    things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"18.001:{address['Address']}\" ]\n"
            #    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <sun>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            # Nachtmodus
            if address['DatapointType'] == 'DPST-1-1':
                if 'Nachtmodus' in address['Group name']:
                    used = True
                    things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\" ]\n"
                    items += f"Switch        {item_name}         \"{lovely_name}\"               <moon>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
            
            if semantic:
                semantic_things += f"Thing device device_{semantic_cnt} \"lovely_name\" @ \"{roomName}\" [ \n"
                semantic_things += " ] { \n"
                semantic_things += f"   Type {thing_type}        : {item_name}        \"{address['Group name']}\"       [ ga=\"{thigs_group_adresses}\" ]\n"
                semantic_things += " } \n"
                items += f"{item_type}        {item_name}         \"{item_Description}\"                <{item_icon}>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:device_{semantic_cnt}:{item_name}\" }}\n"
                semantic_cnt += 1

            if used:
                used_addresses.append(address['Address'])
            if 'influx' in address['Description']:
                print('influx @ ')
                print(address)
                export_to_influx.append(item_name)
    sitemap += f"}}\n "

# process all addresses which were not used
for floorNr in house.keys():
    for roomNr in house[floorNr]['rooms'].keys():
        addresses = house[floorNr]['rooms'][roomNr]['Addresses']
        for i in range(len(addresses)):

            if 'IGNORE' in address.keys():
                continue

            address = house[floorNr]['rooms'][roomNr]['Addresses'][i]
            lovely_name = ' '.join(address['Group name'].replace(house[floorNr]['Group name'],'').replace(house[floorNr]['rooms'][roomNr]['Group name'],'').split())

            item_name = f"i_{cnt}_{house[floorNr]['Group name']}_{house[floorNr]['rooms'][roomNr]['Group name']}_{lovely_name}".replace('/','_').replace(' ','_')
            item_name = item_name.replace('ü','ue').replace('ä','ae').replace('ß','ss')

            if not (address['Address'] in used_addresses):
                #print(address['Group name'])
                if address['DatapointType'] == 'DPST-1-1':
                    #print('^- processed as switch\n')
                    things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\" ]\n"
                    items += f"Switch        {item_name}         \"{lovely_name}\"               <switch>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            #    if address['Group name'].endswith('Status'):
            #        if address['DatapointType'] == 'DPST-1-1':
            #    if 'Nachtmodus' in address['Group name']:
            #        things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}\" ]\n"
            #        items += f"Switch        {item_name}         \"{lovely_name}\"               <moon>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
 

#print(things)
#print(sitemap)
#print(items)

# export things:
things_template = open('things.template','r').read()
things = things_template.replace('###things###', things)
open('../../openhab/things/knx.things','w').write(things)
# export items:
items = 'Group           Home                  "Our Home"                                     [\"Location\"]\n' + items
open('../../openhab/items/knx.items','w').write(items)

# export sitemap:
sitemap_template_file = 'sitemap.template'
if os.path.isfile(f"private_{sitemap_template_file}"):
     sitemap_template_file = f"private_{sitemap_template_file}"
sitemap_template = open(sitemap_template_file,'r').read()
sitemap = sitemap_template.replace('###sitemap###', sitemap)
sitemap = sitemap.replace('###selections###', selections)
open('../../openhab/sitemaps/knx.sitemap','w').write(sitemap)

#export persistent
private_persistence = ''
if os.path.isfile(f"private_persistence"):
     private_persistence = open('private_persistence','r').read()
persist = '''Strategies {
everyMinute : "0 * * * * ?"
everyHour : "0 0 * * * ?"
everyDay : "0 0 0 * * ?"
every2Minutes : "0 */2 * ? * *"
}
 
Items {
'''
for i in export_to_influx:
    persist += f"{i}: strategy = everyUpdate\n"
persist += private_persistence + '\n}'

open('../../openhab/persistence/influxdb.persist','w').write(persist)


print(fensterkontakte)
fenster_rule = ''
for i in fensterkontakte:
    fenster_rule += f'var save_fk_count_{i["item_name"]} = 0 \n'
fenster_rule += '''
rule "fensterkontakt check"
when
    Time cron "0 * * * * ? *"
then
'''
for i in fensterkontakte:
    fenster_rule += f'    if({i["item_name"]}.state == OPEN){{ \n'
    fenster_rule += f'         save_fk_count_{i["item_name"]} += 1\n'
    fenster_rule += f'         if(save_fk_count_{i["item_name"]} == 15) {{\n'
    fenster_rule +=  '             val telegramAction = getActions("telegram","telegram:telegramBot:Telegram_Bot"); \n'
    fenster_rule += f'             telegramAction.sendTelegram("{i["name"]} seit über 15 Minuten offen!");\n'
    fenster_rule +=  '         }\n'
    fenster_rule +=  '    } else { \n'
    fenster_rule += f'        save_fk_count_{i["item_name"]} = 0; \n'
    fenster_rule +=  '    } \n'
fenster_rule += '''
end
'''

open('../../openhab/rules/fenster.rules','w').write(fenster_rule)