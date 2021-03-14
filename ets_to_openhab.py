import csv
import os.path
import json

with open('config.json') as f:
    config = json.load(f)

def data_of_name(data, name):
    for x in data:
        if x['Group name'] == name:
            return x
    return None

csvfile = open(config['ets_export'], newline='', encoding='cp1252')
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
        descriptions = house[floorNr]['rooms'][roomNr]['Description'].split(';')
        visibility = ''
        location = ''
        for description in descriptions:
            if description == 'debug':
                visibility = 'visibility=[extended_view==ON]'
            if description.startswith('location='):
                location = '["' + description.replace('location=','').replace(',','","') + '"] '
        

        items += f"Group   map{floorNr}_{roomNr}   \"{roomName}\"   (map{floorNr})   {location}\n"
        sitemap += f"     Group item=map{floorNr}_{roomNr} {visibility} label=\"{roomName} \" "
        group = ""

        addresses = house[floorNr]['rooms'][roomNr]['Addresses']

        for i in range(len(addresses)):
            used = False
            auto_add = False
            item_icon = None
            sitemap_type = 'Default'
            
            address = house[floorNr]['rooms'][roomNr]['Addresses'][i]
            lovely_name = ' '.join(address['Group name'].replace(house[floorNr]['Group name'],'').replace(house[floorNr]['rooms'][roomNr]['Group name'],'').split())
            
            descriptions = address['Description'].split(';')

            #print(f"--- processing: {lovely_name}")
            #print(address)

            if 'IGNORE' in address.keys():
                continue

            item_name = f"i_{cnt}_{house[floorNr]['Group name']}_{house[floorNr]['rooms'][roomNr]['Group name']}_{lovely_name}".replace('/','_').replace(' ','_')
            item_name = item_name.replace('ü','ue').replace('ä','ae').replace('ß','ss')
            

            # dimmer
            if address['Group name'].endswith(config['defines']['dimmer']['absolut_suffix']):
                basename = address['Group name'].replace(config['defines']['dimmer']['absolut_suffix'],'')
                dimmwert_status = data_of_name(addresses, basename + config['defines']['dimmer']['status_suffix'])
                if dimmwert_status:
                    used = True
                    used_addresses.append(dimmwert_status['Address'])
                    # drop possible unused GAs
                    for drop_name in config['defines']['dimmer']['drop']:
                        drop_addr = data_of_name(addresses, basename + drop_name)
                        if drop_addr:
                             used_addresses.append(drop_addr['Address'])

                    lovely_name = ' '.join(lovely_name.replace('Dimmen','').replace('Dimmer','').replace('absolut','').replace('Licht','').split())
                    things += f"Type dimmer        : {item_name}        \"{address['Group name'].replace('absolut','')}\"        "
                    things += f"[ position=\"{address['Address']}+<{dimmwert_status['Address']}\"]\n"
                    items += f"Dimmer        {item_name}         \"{lovely_name} [%d %%]\"               <light>  (map{floorNr}_{roomNr})    [\"Lightbulb\"]    {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    group += f"        Default item={item_name} label=\"{lovely_name} [%d %%]\" {visibility}\n"

            # Schalten, Präsenz, Nachtmodus oder Fensterkontakte
            if address['DatapointType'] == 'DPST-1-1':
                item_type = "Switch"
                thing_address_info = f"ga=\"{address['Address']}\""
                item_label = lovely_name
                if 'Präsenz' in address['Group name']:
                    auto_add = True
                    semantic_info = "[\"MotionDetector\", \"Presence\"]"
                    item_icon = "motion" 
                if 'Nachtmodus' in address['Group name']:
                    auto_add = True
                    semantic_info = "[\"Control\"]"
                    item_icon = "moon" 
                if config['defines']['contact']['suffix'] in address['Group name']:
                    item_type = "Contact"
                    auto_add = True
                    semantic_info = "[\"Window\", \"OpenState\"]"
                    # shorten name if possible
                    lovely_name_short = ' '.join(lovely_name.replace(config['defines']['contact']['suffix'],'').split())
                    if lovely_name_short != '':
                        lovely_name = lovely_name_short
                    fensterkontakte.append({'item_name': item_name, 'name': address['Group name']})
                # umschalten (Licht, Steckdosen)
                if not address['Group name'].endswith(' '+config['defines']['switch']['status_suffix']):
                    status = data_of_name(addresses, address['Group name'] + ' ' + config['defines']['switch']['status_suffix'])
                    if status:
                        auto_add = True
                        used_addresses.append(status['Address'])
                        
                        semantic_info = "[\"Lightbulb\"]"
                        item_icon = 'light'
                        if 'Steckdose' in address['Group name']:
                            semantic_info = "[\"PowerOutlet\"]"
                            item_icon = 'poweroutlet'
                        if 'Audio' in address['Group name']:
                            semantic_info = "[\"Speaker\"]"
                            item_icon = 'soundvolume'
                        # remove generic description if unneccessary
                        lovely_name_short = ' '.join(lovely_name.replace('Licht','').replace('Steckdose','').replace('Steckdosen','').split())
                        if lovely_name_short != '':
                            lovely_name = lovely_name_short
                        #things += f"Type switch        : {item_name}        \"{address['Group name']}\"       [ ga=\"{address['Address']}+<{status['Address']}\" ]\n"
                        #items += f"Switch        {item_name}         \"{lovely_name}\"               <{typ}>  (map{floorNr}_{roomNr})     [\"{semantic_type}\"]      {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                        #group += f"        Default item={item_name} label=\"{lovely_name}\" {visibility}\n"

        ######## determined by datapoint
            # temperatur
            if address['DatapointType'] == 'DPST-9-1':
                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"9.001:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f °C]"

                semantic_info = "[\"Measurement\", \"Temperature\"]"
                if 'Soll' in lovely_name:
                    semantic_info = "[\"Setpoint\", \"Temperature\"]"
                
                item_icon = "temperature" 

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

                    auto_add = True
                    item_type = "Rollershutter"
                    thing_address_info = f"upDown=\"{fahren_auf_ab['Address']}\", stopMove=\"{fahren_stop['Address']}\", position=\"{absolute_position['Address']}+<{absolute_position_status['Address']}\""
                    item_label = f"{lovely_name} [%d %%]"
                    semantic_info = "[\"Blinds\"]"
                else:
                    print(f"incomplete rollershutter: {basename}")

            # Arbeit (wh)
            if address['DatapointType'] == 'DPST-13-10':
                lovely_name = ' '.join(lovely_name.replace('Leistung','').split())

                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"13.010:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f Wh]"
                semantic_info = "[\"Measurement\", \"Energy\"]"
                item_icon = "batterylevel"

            # Leistung (W)
            if address['DatapointType'] == 'DPST-14-56':
                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"14.056:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f W]"
                semantic_info = "[\"Measurement\", \"Power\"]"
                item_icon = "batterylevel"

            # Strom
            if address['DatapointType'] == 'DPST-7-12':
                lovely_name = ' '.join(lovely_name.replace('Strom','').replace('aktuell','').split())

                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"7.012:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f mA]"
                semantic_info = "[\"Measurement\", \"Current\"]"
                item_icon = "batterylevel"

            # Lux
            if address['DatapointType'] == 'DPST-9-4':
                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"9.004:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f Lux]"
                semantic_info = "[\"Measurement\", \"Light\"]"
                item_icon = "sun"

            # Geschwindigkeit m/s
            if address['DatapointType'] == 'DPST-9-5':
                auto_add = True
                item_type = "Number"
                thing_address_info = f"ga=\"9.005:{address['Address']}\""
                item_label = f"{lovely_name} [%.1f m/s]"
                semantic_info = "[\"Measurement\", \"Wind\"]"
                item_icon = "wind"

            # Szene
            if address['DatapointType'] == 'DPST-17-1':
                print(address)
                used = True
                mappings=''

                #things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ga=\"17.001:{address['Address']}\"]\n"
                
                if 'mappings' in address['Description']:
                    #TODO: split other values
                    mapfile = f"gen_{item_name}.map"
                    mappings = address['Description'].replace("'",'"')
                    #TODO: move this
                    
                    #items += f"Number        {item_name}         \"{lovely_name} [MAP({mapfile}):%s]\"               <movecontrol>          {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    #group += f"        Selection item={item_name} label=\"{lovely_name}\"  {mappings} {visibility}\n"
                    mapfile_content = mappings.replace('"','').replace(',','\n').replace('mappings=[','').replace(']','').replace(' ','')
                    mapfile_content += '\n' + mapfile_content.replace('=','.0=') + '\n-=unknown'
                    open(os.path.join(config['transform_dir_path'], mapfile),'w').write(mapfile_content)

                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"17.001:{address['Address']}\""
                    item_label = f"{lovely_name} [MAP({mapfile}):%s]"
                    semantic_info = "[\"Control\"]"
                    item_icon = "movecontrol"
                    visibility  = f"{mappings} {visibility}"
                    sitemap_type = "Selection"

                #else:
                #    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <movecontrol>          {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                #    group += f"        Selection item={item_name} label=\"{lovely_name}\"  {visibility}\n"
                
            # Szenensteuerung
            #if address['DatapointType'] == 'DPST-18-1':
            #    print(address)
            #    used = True
            #    things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"18.001:{address['Address']}\" ]\n"
            #    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <sun>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

            if auto_add:

                visibility = ''
                for description in descriptions:
                    if 'debug' in description:
                        visibility = 'visibility=[extended_view==ON]'
                    if description.startswith('semantic='):
                        semantic_info = '["' + description.replace('semantic=','').replace(',','","') + '"] '
                    if description.startswith('icon='):
                        item_icon = description.replace('icon=','').replace(',','","')

                used = True
                if item_icon:
                    item_icon = f"<{item_icon}>"
                else: 
                    item_icon = ""
                thing_type = item_type.lower()
                things += f"Type {thing_type}    :   {item_name}   \"{address['Group name']}\"   [ {thing_address_info} ]\n"
                items += f"{item_type}   {item_name}   \"{item_label}\"   {item_icon}   (map{floorNr}_{roomNr})   {semantic_info}    {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                group += f"        {sitemap_type} item={item_name} label=\"{item_label}\" {visibility}\n"

            if used:
                used_addresses.append(address['Address'])
            if 'influx' in address['Description']:
                #print('influx @ ')
                #print(address)
                export_to_influx.append(item_name)

        if group != '':
            sitemap += f" {{\n{group}\n    }}\n"
        else:
            sitemap += f"\n "
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
                    items += f"Switch        {item_name}         \"{lovely_name}\"               <switch>    (map{floorNr}_{roomNr})       {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    group += f"        Default item={item_name} label=\"{lovely_name}\" {visibility}\n"

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
open(config['things_path'],'w').write(things)
# export items:
items = 'Group           Home                  "Our Home"                                     [\"Location\"]\n' + items
open(config['items_path'],'w').write(items)

# export sitemap:
sitemap_template_file = 'sitemap.template'
if os.path.isfile(f"private_{sitemap_template_file}"):
     sitemap_template_file = f"private_{sitemap_template_file}"
sitemap_template = open(sitemap_template_file,'r').read()
sitemap = sitemap_template.replace('###sitemap###', sitemap)
sitemap = sitemap.replace('###selections###', selections)
open(config['sitemaps_path'],'w').write(sitemap)

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

open(config['influx_path'],'w').write(persist)


#print(fensterkontakte)
#fenster_rule = ''
#for i in fensterkontakte:
#    fenster_rule += f'var save_fk_count_{i["item_name"]} = 0 \n'
#fenster_rule += '''
#rule "fensterkontakt check"
#when
#    Time cron "0 * * * * ? *"
#then
#'''
#for i in fensterkontakte:
#    fenster_rule += f'    if({i["item_name"]}.state == OPEN){{ \n'
#    fenster_rule += f'         save_fk_count_{i["item_name"]} += 1\n'
#    fenster_rule += f'         if(save_fk_count_{i["item_name"]} == 15) {{\n'
#    fenster_rule +=  '             val telegramAction = getActions("telegram","telegram:telegramBot:Telegram_Bot"); \n'
#    fenster_rule += f'             telegramAction.sendTelegram("{i["name"]} seit über 15 Minuten offen!");\n'
#    fenster_rule +=  '         }\n'
#    fenster_rule +=  '    } else { \n'
#    fenster_rule += f'        save_fk_count_{i["item_name"]} = 0; \n'
#    fenster_rule +=  '    } \n'
#fenster_rule += '''
#end
#'''
#
#open('../../openhab/rules/fenster.rules','w').write(fenster_rule)