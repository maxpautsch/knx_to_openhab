# KNX to openhab generator
Generate an openhab text configuration based on an ETS GA export. 
Despite all things and items, the sitemap for basicui is generated. The semantic model is supported. 

## Export GAs:
Select all GAs in ETS. Exportformat: CSV. Format 1/1 "Name/Adresse", SCV Seperator Tabulator. The GAs should follow the scheme floor/room/message.

## Run
- edit `config.json`
    - the default locations for the output files match directly, if you create a `openhab` directory and mount the `/etc/openhab` there. (under linux use e.g. `sshfs pi@[myIP]:/etc/openhab openhab`)
- run `python3 ets_to_openhab.py`

## drop words
Within the configuration, there is a field `drop_words`. There you can define words which should not be used in labels. E.g. lights have already a bulb symbol. So the word light is not needed in the description. However, if the description would be empty after cleanup, the words are not dropped! (e.g. you have a `light right` and a `light left` -> bulb symbols with the words `right` and `left`. If you have only one light, the name will not be shortend as it is already short ;) )

## ETS description field

there are some addons based on the description field of the GA in ETS. Multiple options are seperated by a semicolon. 
- add `influx` to automatically save the values to influxDB.
- add `debug` to add a visibility tag to a element. Use item `extended_view` to change visibility.
- scene mappings: see below
- add `location` to add the [location](https://github.com/openhab/openhab-core/blob/main/bundles/org.openhab.core.semantics/model/SemanticTags.csv) to the first two layers of group addresses. Divide multiple by `,` 
- add `semantic` to overwrite the default entries. (e.g. if a switch is controlling a projector: semantic=Projector). [Possible options](https://github.com/openhab/openhab-core/blob/main/bundles/org.openhab.core.semantics/model/SemanticTags.csv). Divide multiple by `,`  
- add `icon` to set the icon. e.g. `icon=projector`

(e.g. `semantic=Pump;icon=pump;debug;influx`)

## Processed types:
### Components determined only by GA
- Temperature based on Datatype
- Window Contact - based on Datatype 1.019
- Electrical work (wh) based on Datatype    
- Power (W) based on Datatype
- Curent based on Datatype
- Lux based on Datatype
- Day/Night based on Datatype 1.024
- Alarm based on Datatype 1.005
- Speed m/s based on Datatype
- Timedifference based on Datatype 13.100
- Scene based on Datatype. Add for example `mappings=[63='Aus', 62='Automatik', 1='Kochen', 2='Beamer', 3='Allgemein']` to description in ETS to generate automatic mapping. MAP transformation plugin required!

### Components which need a naming scheme
- Rollershutter based on Name
- Switch - based on Datatype. Looking for a status GA with the same name and suffix configured in config.json/"switch"/"status_suffix". Default: "Status" 
    - Example: GAs "Light right" + "Light right Status"
    - Lights, powerplugs and audio devices can be detected by names configured at config.json -> defines -> switch -  "poweroutlet_name" / "speaker_name" / "light_name". The configured name has to be part of the GA Name.
- Dimmer - based on suffix in config.json/"dimmer"/"suffix_absolut" (default: "Dimmen absolut"). Also searching for: "status_suffix" (default "Status Dimmwert") Dropping all GA suffixes within config.json/"dimmer"/"drop".
    -  Example: GAs "Light Dimmen absolut" + "Light Status Dimmwert"