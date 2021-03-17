# knx_to_openhab
Generate openhab configuration (semantic model as also sitemap for basicui) based on ETS export

## Export GAs:
Select all GAs in ETS. Exportformat: CSV. Format 1/1 "Name/Adresse", SCV Seperator Tabulator. The GAs should follow the scheme floor/room/message.

## Run
- edit `config.json`
- run `python3 ets_to_openhab.py`

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
- Temperature based on Datatype
- Switch - based on Datatype. Looking for a status GA with the same name and suffix configured in config.json/"switch"/"status_suffix". Default: "Status" 
    - Example: GAs "Light right" + "Light right Status"
- Dimmer - based on suffix in config.json/"dimmer"/"suffix_absolut" (default: "Dimmen absolut"). Also searching for: "status_suffix" (default "Status Dimmwert") Dropping all GA suffixes within config.json/"dimmer"/"drop".
    -  Example: GAs "Light Dimmen absolut" + "Light Status Dimmwert"
- Window Contact - based on Datatype (DPST-1-19)
- Electrical work (wh) based on Datatype    
- Power (W) based on Datatype
- Curent based on Datatype
- Lux based on Datatype
- Speed m/s based on Datatype
- Timedifference based on Datatype (DPST-13-100)
- Scene based on Datatype. Add for example `mappings=[63='Aus', 62='Automatik', 1='Kochen', 2='Beamer', 3='Allgemein']` to description in ETS to generate automatic mapping. MAP transformation plugin required!
- Rollershutter 
