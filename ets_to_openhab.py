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
    #print(row)
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
    descriptions = house[floorNr]['Description'].split(';')
    visibility = ''
    semantic = ''
    synonyms = ''
    icon = ''
    for description in descriptions:
        if description == 'debug':
            visibility = 'visibility=[extended_view==ON]'
        if description.startswith('icon='):
            icon = '<' + description.replace('icon=','') + '>'
        if description.startswith('semantic='):
            semantic = '["' + description.replace('semantic=','').replace(',','","') + '"] '
        if description.startswith('synonyms='):
           synonyms = '{ ' + description.replace('synonyms=','synonyms="').replace(',',', ') + '" } '

    items += f"Group   map{floorNr}   \"{house[floorNr]['Group name']}\" {icon}  {semantic} {synonyms} \n" # {location}  \n" # {visibility}
    sitemap += f"Frame label=\"{house[floorNr]['Group name']}\" {{\n"

    for roomNr in house[floorNr]['rooms'].keys():
        roomName = house[floorNr]['rooms'][roomNr]['Group name']
        descriptions = house[floorNr]['rooms'][roomNr]['Description'].split(';')
        visibility = ''
        semantic = f"[\"Room\", \"{roomName}\"]"
        icon = ''
        synonyms = ''
        for description in descriptions:
            if description == 'debug':
                visibility = 'visibility=[extended_view==ON]'
            if description.startswith('icon='):
                icon = '<' + description.replace('icon=','') + '>'
            if description.startswith('semantic='):
                semantic = '["' + description.replace('semantic=','').replace(',','","') + '"] '
            if description.startswith('synonyms='):
                synonyms = '{ ' + description.replace('synonyms=','synonyms="').replace(',',', ') + '" } '
            if description.startswith('name='):
                roomName = description.replace('name=','')

        items += f"Group   map{floorNr}_{roomNr}   \"{roomName}\"  {icon}  (map{floorNr})   {semantic} {synonyms}\n"
        sitemap += f"     Group item=map{floorNr}_{roomNr} {visibility} label=\"{roomName}\" "
        group = ""

        addresses = house[floorNr]['rooms'][roomNr]['Addresses']

        # the loop has to be executed twice.
        # - during the first run, all GAs are processed which can have a reference to another GA (e.g. a switch with status feedback)
        #   and also all GAs which can not have a reference to another GA. (e.g. temperatures)
        # - during the second run, all not marked componentes are processed directly with no reference check
        for run in [0, 1]:
            for i in range(len(addresses)):

                address = house[floorNr]['rooms'][roomNr]['Addresses'][i]
                # in the second run: only process not already used addresses
                if run == 1:
                    if address['Address'] in used_addresses:
                        continue

                used = False
                auto_add = False
                item_icon = None
                sitemap_type = 'Default'
                mappings = ''
                lovely_name = ' '.join(address['Group name'].replace(house[floorNr]['rooms'][roomNr]['Group name'],'').replace(house[floorNr]['Group name'],'').split())
                item_label = lovely_name
                descriptions = address['Description'].split(';')
                equipment = ''

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
                        switch_option = ''
                        relative_option = ''
                        used_addresses.append(dimmwert_status['Address'])

                        relative_command = data_of_name(addresses, basename + config['defines']['dimmer']['relativ_suffix'])

                        if relative_command:
                            used_addresses.append(relative_command['Address'])
                            relative_option = f", increaseDecrease=\"{relative_command['Address']}\""

                        switch_command = data_of_name(addresses, basename + config['defines']['dimmer']['switch_suffix'])
                        if switch_command:
                            used_addresses.append(switch_command['Address'])
                            switch_status_command = data_of_name(addresses, basename + config['defines']['dimmer']['switch_status_suffix'])
                            switch_option_status = ''
                            if switch_status_command:
                                used_addresses.append(switch_status_command['Address'])
                                switch_option_status = f"+<{switch_status_command['Address']}"
                            switch_option = f", switch=\"{switch_command['Address']}{switch_option_status}\""
                        
                        lovely_name = ' '.join(lovely_name.replace('Dimmen','').replace('Dimmer','').replace('absolut','').replace('Licht','').split())

                        auto_add = True
                        item_type = "Dimmer"
                        item_label = f"{lovely_name} [%d %%]"
                        thing_address_info = f"position=\"{address['Address']}+<{dimmwert_status['Address']}\"{switch_option}{relative_option}"
                        item_icon = "light"
                        equipment = 'Lightbulb'
                        semantic_info = "[\"Light\"]"

                # rollos / jalousien
                if address['DatapointType'] == 'DPST-1-8':
                    if not address['Group name'].endswith(config['defines']['rollershutter']['up_down_suffix']):
                        continue
                    
                    basename = address['Group name'].replace(config['defines']['rollershutter']['up_down_suffix'],'')
                    fahren_auf_ab = data_of_name(addresses, basename + config['defines']['rollershutter']['up_down_suffix'])
                    fahren_stop = data_of_name(addresses, basename + config['defines']['rollershutter']['stop_suffix'])
                    absolute_position = data_of_name(addresses, basename + config['defines']['rollershutter']['absolute_position_suffix'])
                    absolute_position_status = data_of_name(addresses, basename + config['defines']['rollershutter']['status_suffix'])
                    #Status Richtung nicht in verwendung durch openhab
                    for drop_name in config['defines']['rollershutter']['drop']:
                        drop_addr = data_of_name(addresses, basename + drop_name)
                        if drop_addr:
                            used_addresses.append(drop_addr['Address'])

                    lovely_name = basename
                    
                    if fahren_auf_ab and fahren_stop and absolute_position and absolute_position_status:
                        used_addresses.append(fahren_auf_ab['Address'])
                        used_addresses.append(fahren_stop['Address'])
                        used_addresses.append(absolute_position['Address'])
                        used_addresses.append(absolute_position_status['Address'])

                        auto_add = True
                        item_type = "Rollershutter"
                        thing_address_info = f"upDown=\"{fahren_auf_ab['Address']}\", stopMove=\"{fahren_stop['Address']}\", position=\"{absolute_position['Address']}+<{absolute_position_status['Address']}\""
                        item_label = f"{lovely_name} [%d %%]"
                        semantic_info = "[\"Blinds\"]"
                        item_icon = "rollershutter"
                    else:
                        print(f"incomplete rollershutter: {basename}")

                # Schalten
                if address['DatapointType'] == 'DPST-1-1':
                    item_type = "Switch"
                    item_icon = "switch"
                    item_label = lovely_name
                    # umschalten (Licht, Steckdosen)
                    # only add in first round, if there is a status GA for feedback
                    if not address['Group name'].endswith(' '+config['defines']['switch']['status_suffix']):
                        status = data_of_name(addresses, address['Group name'] + ' ' + config['defines']['switch']['status_suffix'])
                        if status:
                            #if status['DatapointType'] == 'DPST-1-11':
                                auto_add = True
                                used_addresses.append(status['Address'])
                                thing_address_info = f"ga=\"{address['Address']}+{status['Address']}\""

                    # in the second run, we accept everything ;)
                    if run == 1:
                        auto_add = True
                        thing_address_info = f"ga=\"1.001:{address['Address']}\""
                        item_label = f"{lovely_name} [%d]"
                        semantic_info = "[\"Control\", \"Status\"]"

                    if config['defines']['switch']['light_name'] in address['Group name']:
                        semantic_info = "[\"Light\"]"
                        equipment = 'Lightbulb'
                        item_icon = 'light'
                    if config['defines']['switch']['poweroutlet_name'] in address['Group name']:
                        semantic_info = "[\"Switch\"]"
                        equipment = 'PowerOutlet'
                        item_icon = 'poweroutlet'
                    if config['defines']['switch']['speaker_name'] in address['Group name']:
                        semantic_info = "[\"Switch\"]"
                        equipment = 'Speaker'
                        item_icon = 'soundvolume'


                ######## determined only by datapoint

                # temperature
                if address['DatapointType'] == 'DPST-9-1':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"9.001:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f °C]"

                    semantic_info = "[\"Measurement\", \"Temperature\"]"
                    if 'Soll' in lovely_name:
                        semantic_info = "[\"Setpoint\", \"Temperature\"]"
                    
                    item_icon = "temperature" 

                # humidity
                if address['DatapointType'] == 'DPST-9-7':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"9.007:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f %%RHD]"

                    semantic_info = "[\"Measurement\", \"Humidity\"]"
                    if 'Soll' in lovely_name:
                        semantic_info = "[\"Setpoint\", \"Humidity\"]"
                    
                    item_icon = "humidity" 

                # window/door
                if address['DatapointType'] == 'DPST-1-19':
                    auto_add = True
                    item_type = "Contact"
                    thing_address_info = f"ga=\"1.019:{address['Address']}\""
                    equipment = 'Window'
                    semantic_info = "[\"Status\", \"Opening\"]"

                    fensterkontakte.append({'item_name': item_name, 'name': address['Group name']})

                # Arbeit (wh)
                if address['DatapointType'] == 'DPST-13-10':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"13.010:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f Wh]"
                    semantic_info = "[\"Measurement\", \"Energy\"]"
                    item_icon = "batterylevel"

                # Tag/Nacht
                if address['DatapointType'] == 'DPST-1-24':
                    auto_add = True
                    item_type = "Switch"
                    thing_address_info = f"ga=\"1.024:{address['Address']}\""
                    item_label = f"{lovely_name}"
                    semantic_info = "[\"Control\"]"
                    item_icon = "moon"

                # Alarm
                if address['DatapointType'] == 'DPST-1-5':
                    auto_add = True
                    item_type = "Switch"
                    thing_address_info = f"ga=\"1.005:{address['Address']}\""
                    item_label = f"{lovely_name}"
                    semantic_info = "[\"Alarm\"]"
                    item_icon = "alarm"

                # Leistung (W)
                if address['DatapointType'] == 'DPST-14-56':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"14.056:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f W]"
                    semantic_info = "[\"Measurement\", \"Power\"]"
                    item_icon = "energy"

                # Strom
                if address['DatapointType'] == 'DPST-7-12':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"7.012:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f mA]"
                    semantic_info = "[\"Measurement\", \"Current\"]"
                    item_icon = "energy"

                # String
                if address['DatapointType'] == 'DPST-16-0':
                    auto_add = True
                    item_type = "String"
                    thing_address_info = f"ga=\"16.000:{address['Address']}\""
                    item_icon = "text"

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

                # Zeitdifferenz 
                if address['DatapointType'] == 'DPST-13-100':
                    auto_add = True
                    item_type = "Number"
                    thing_address_info = f"ga=\"13.100:{address['Address']}\""
                    item_label = f"{lovely_name} [%.1f s]"
                    semantic_info = "[\"Measurement\", \"Duration\"]"
                    item_icon = "time"

                # Szene
                if address['DatapointType'] == 'DPST-17-1':
                    used = True
                    
                    for description in descriptions:
                        if description.startswith('mappings='):
                            mappings = description
                            break

                    if mappings!= '':
                        mapfile = f"gen_{item_name}.map"
                        mappings = mappings.replace("'",'"')

                        mapfile_content = mappings.replace('"','').replace(',','\n').replace('mappings=[','').replace(']','').replace(' ','')
                        mapfile_content += '\n' + mapfile_content.replace('=','.0=') + '\n-=unknown'
                        open(os.path.join(config['transform_dir_path'], mapfile),'w').write(mapfile_content)

                        auto_add = True
                        item_type = "Number"
                        thing_address_info = f"ga=\"17.001:{address['Address']}\""
                        item_label = f"{lovely_name} [MAP({mapfile}):%s]"
                        semantic_info = "[\"Control\"]"
                        item_icon = "movecontrol"
                        sitemap_type = "Selection"
                    else:
                        print(f"no mapping for scene {address['Address']} {address['Group name']} ")
                    #else:
                    #    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <movecontrol>          {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"
                    #    group += f"        Selection item={item_name} label=\"{lovely_name}\"  {visibility}\n"
                    
                # Szenensteuerung
                #if address['DatapointType'] == 'DPST-18-1':
                #    print(address)
                #    used = True
                #    things += f"Type number        : {item_name}        \"{address['Group name']}\"       [ ga=\"18.001:{address['Address']}\" ]\n"
                #    items += f"Number        {item_name}         \"{lovely_name} [%d]\"                <sun>  (map{floorNr}_{roomNr})        {{ channel=\"knx:device:bridge:generic:{item_name}\" }}\n"

                # some components are only processed in the second run
                # e.g. the state datapoint could be an own thing or the feedback from a switch or so
                if run == 1:
                    # Status
                    if address['DatapointType'] == 'DPST-1-11':
                        auto_add = True
                        item_type = "Switch"
                        thing_address_info = f"ga=\"1.011:{address['Address']}\""
                        item_label = f"{lovely_name} [%d]"
                        semantic_info = "[\"Measurement\", \"Status\"]"
                        item_icon = "switch"

                # TODO: get rid of this
                if used:
                    used_addresses.append(address['Address'])

                if auto_add:
                    synonyms = ''
                    used_addresses.append(address['Address'])
                    visibility = ''
                    for description in descriptions:
                        if 'debug' in description:
                            visibility = 'visibility=[extended_view==ON]'
                        if description.startswith('semantic='):
                            semantic_info = '["' + description.replace('semantic=','').replace(',','","') + '"] '
                        if description.startswith('icon='):
                            item_icon = description.replace('icon=','').replace(',','","')
                        if description.startswith('synonyms='):
                            synonyms = '{ ' + description.replace('synonyms=','synonyms="').replace(',',', ') + '" } '
                        if description.startswith('name='):
                            item_label = description.replace('name=','')
                    # remove generic description if unneccessary
                    item_label_short = item_label
                    for drop in config['defines']['drop_words']:
                            item_label_short = item_label_short.replace(drop,'')
                    item_label_short = ' '.join(item_label_short.split())
                    if item_label_short != '':
                        item_label = item_label_short

                    if item_icon:
                        item_icon = f"<{item_icon}>"
                    else: 
                        item_icon = ""

                    thing_type = item_type.lower()
                    things += f"Type {thing_type}    :   {item_name}   \"{address['Group name']}\"   [ {thing_address_info} ]\n"

                    root = f"map{floorNr}_{roomNr}"
                    if equipment != '':
                        items += f"Group   equipment_{item_name}   \"{item_label}\"  {item_icon}  ({root})   [\"{equipment}\"]\n"
                        root = f"equipment_{item_name}"

                    items += f"{item_type}   {item_name}   \"{item_label}\"   {item_icon}   ({root})   {semantic_info}    {{ channel=\"knx:device:bridge:generic:{item_name}\" {synonyms} }}\n"
                    group += f"        {sitemap_type} item={item_name} label=\"{item_label}\" {mappings} {visibility}\n"

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
                print(f"unused: {address['Address']}: {address['Group name']} with type {address['DatapointType']}")
                
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

