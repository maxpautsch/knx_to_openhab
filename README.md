# knx_to_openhab
Generate openhab configuration based on ETS export

## Export GAs:
Select all GAs in ETS. Exportformat: CSV. Format 1/1 "Name/Adresse", SCV Seperator Tabulator.

## Run
- edit `config.json`
- run `python3 ets_to_openhab.py`

## Persistence

add 'influx' as description of GA within ETS to automatically save the values to influxDB.

## Processed types:
- Temperature  based on Datatype
- Switch - based on Datatype. Looking for a status GA with the same name and suffix configured in config.json/"switch"/"status_suffix". Default: "Status" 
    - Example: GAs "Light right" + "Light right Status"
- Dimmer - based on suffix in config.json/"dimmer"/"suffix_absolut" (default: "Dimmen absolut"). Also searching for: "status_suffix" (default "Status Dimmwert") Dropping all GA suffixes within config.json/"dimmer"/"drop".
    -  Example: GAs "Light Dimmen absolut" + "Light Status Dimmwert"
- Window Contact - based on Name configured at 
- Electrical work (wh) based on Datatype    
- Power (W) based on Datatype
- Curent based on Datatype
- Lux based on Datatype
- Speed m/s based on Datatype
- Scene based on Datatype. Add for example `mappings=[63='Aus', 62='Automatik', 1='Kochen', 2='Beamer', 3='Allgemein']` to description in ETS to generate automatic mapping
- Rollershutter 
