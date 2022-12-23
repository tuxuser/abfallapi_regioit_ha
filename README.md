[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

# Home Assistant sensor for german waste collection schedule (regioIT API)

## Functionality

The sensor shows the bin which will be collected the next day. The complete collection schedule is available as attributes of the sensor

Supported services:

* Bergisch Gladbach (AWB / Neuenhaus)
* Lindlar
* ZEW
* Dinslaken
* Pinneberg
* Lüdenscheid
* Bergischer Abfallwirtschaftverbund
* WML
* KRWAF AWG / GEG
* Aachen
* Dorsten
* Gütersloh
* Halver
* Coesfeld
* Norderstedt
* Solingen
* Nürnberg (Stadt)

![alt text](https://github.com/tuxuser/abfallapi_regioit_ha/blob/master/preview1.png "glance card")

![alt text](https://github.com/tuxuser/abfallapi_regioit_ha/blob/master/preview2.png "glance card details")

## Credits

Based on [AWB Köln Home Assistant sensor](https://github.com/jensweimann/awb) by [jensweimann](https://github.com/jensweimann)

## Installation

### Manual

Copy all files from custom_components/abfallapi_regioit/ to custom_components/abfallapi_regioit/ inside your config Home Assistant directory.

### HACS

Search for `Abfall API (RegioIT)` in HACS -> Integrations.
Install the integration and restart home assistant.

## Discussion

[Home Assistant Community Forum](https://community.home-assistant.io/t/german-mullabfuhr-sensor/168244)

## Configuration

### Setup sensor

```yaml
- platform: abfallapi_regioit
  name: muellabfuhr
  scan_interval: 3600
  anbieter_id: KRWAF
  ort: 'Ahlen'
  strasse: 'Abtstraße'
```

### Customize

```yaml
sensor.muellabfuhr:
  friendly_name: Heute Mülltonne rausstellen
  icon: mdi:delete
```

### Automation

```yaml
- alias: Abfall Notification
  trigger:
    - platform: time
      at: "18:00:00"
    - entity_id: binary_sensor.someone_is_home
      from: 'off'
      platform: state
      to: 'on'
  condition:
    - condition: and
      conditions:
      - condition: time
        after: '09:00:00'
      - condition: time
        before: '23:00:00'
      - condition: template
        value_template: "{{ (states.sensor.muellabfuhr.state != 'Keine') and (states.sensor.muellabfuhr.state != 'unknown') }}"
  action:
    - service: notify.my_telegram
      data_template:
        message: "{{ states.sensor.muellabfuhr.state }}"
```

### Find anbieter_id

BASE_URL can be found in [regioit_abfall_api.py](https://github.com/tuxuser/abfallapi_regioit_ha/blob/master/custom_components/abfallapi_regioit/regioit_abfall_api.py#L48) -> CITIES

```yaml
anbieter_id: KRWAF
```

### Verify names for strasse and ort

`GET https://<BASE_URL>/rest/orte`

Example output:

```json
[
 {"id":3839714,"name":"Ahlen"},
 {"id":3840376,"name":"Beckum"},
 ...
]
```

`GET http://<BASE_URL>/rest/orte/<ort_id>/strassen`

Example output:

```json
[
 {"id":3839716,"name":"Abtstraße","hausNrList":[],"ort":{"id":3839714,"name":"Ahlen"}},
 {"id":3839725,"name":"Agnes-Miegel-Straße","hausNrList":[],"ort":{"id":3839714,"name":"Ahlen"}},
 ...
]
```

## DISCLAIMER

This project is in no way endorsed by or affiliated with regioIT, or any associated subsidiaries, logos or trademarks.
