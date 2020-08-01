from django.shortcuts import render
from django.http import HttpResponse
from django.views.defaults import bad_request

from character.models import CorporationName

from utils import SNI_URL, SNI_DYNAMIC_TOKEN, SNI_TEMP_USER_TOKEN
import SNI.esi as esi
from SNI.check import check_tokens
from SNI.lib import global_headers, get_clearance_level

import datetime
import requests

from SNI.error import render_error

CORPORATION_HISTORY_LIMIT = 15  # for not overloading the page when people went in way too much corporations

GLOBAL_URL = SNI_URL + "user"


@check_tokens()
def home(request):
    """
    Will display all the characters registered on the SNI
    """

    request_characters = requests.get(GLOBAL_URL, headers=global_headers(request))

    if request_characters.status_code != 200:
        return render_error(request_characters)

    character_list = request_characters.json()

    # Remove root from the list as it is not a truly valid character
    root = next((item for item in character_list if item["character_name"] == "root"), None)
    if root != None:
        character_list.remove(root)

    return render(request, 'character/home.html', {"character_list": character_list})


@check_tokens()
def sheet(request, character_id):
    """
    Will display the main page for accessing charachter informations
    """

    # Get data from ESI
    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    character = request_name.json()

    corp_history = esi.get_corporation_history(character_id).json()
    if len(corp_history) > CORPORATION_HISTORY_LIMIT:
        corp_history = corp_history[0:CORPORATION_HISTORY_LIMIT-1]
        shortend_corp_hist = True
    else:
        shortend_corp_hist = False

    for corp in corp_history:
        corp_id = corp["corporation_id"]
        try:
            corp_name = CorporationName.objects.get(corporation_id=corp["corporation_id"]).corporation_name
        except CorporationName.DoesNotExist:
            corp_name_request = esi.post_universe_names(corp_id)
            corp_name = corp_name_request.json()[0]["name"]
            db_entry = CorporationName(corporation_id=corp_id, corporation_name=corp_name)
            db_entry.save()
        corp["corporation_name"] = corp_name
        start_date = datetime.datetime.strptime(corp["start_date"], "%Y-%m-%dT%H:%M:%S%z")
        corp["start_date"] = f"{start_date.day}/{start_date.month}/{start_date.year} , {start_date.hour}:{start_date.minute}"

    #Getting Clone location
    url = f"{SNI_URL}esi/latest/characters/{character_id}/clones/"
    data="{\"on_behalf_of\": "+ str(character_id) + "}"
    request_clone = requests.get(url, headers=global_headers(request), data=data)
    if request_clone.status_code != 200:
        return render_error(request_clone)

    clone_data = request_clone.json()["data"]

    clone_list = list()
    if "jump_clones" in clone_data:
        for clones in clone_data["jump_clones"]:
            if clones["location_type"] == "structure" :
                structure_id = clones["location_id"]
                url_structure = f"{SNI_URL}esi/latest/universe/structures/{structure_id}/"
                data="{\"on_behalf_of\": "+ str(character_id) + "}"
                request_structure = requests.get(url_structure, headers=global_headers(request), data=data)

                if request_structure.status_code != 200:
                    return render_error(request_structure)
                
                structure_data = request_structure.json()["data"]

                if "error" in structure_data:
                    clone_list.append("Name not readable - not on ACL")
                elif "name" in structure_data:
                    clone_list.append(structure_data["name"])
                else:
                    clone_list.append("I found a strange structure, contact the site admin...")

            elif clones["location_type"] == "station" :
                station_id = clones["location_id"]
                url_station = f"{SNI_URL}esi/latest/universe/stations/{station_id}/"
                request_station = requests.get(url_station, headers=global_headers(request))

                if request_station.status_code != 200:
                    return render_error(request_station)
                
                station_data = request_station.json()["data"]

                if "error" in station_data:
                    clone_list.append("Name not readable - not on ACL")
                elif "name" in station_data:
                    clone_list.append(station_data["name"])
                else:
                    clone_list.append("A station without name!? contact the site admin...")
            else:
                clone_list.append("this was unexpected, contact the site admin...")
    print(clone_list)

    return render(request, 'character/sheet.html', {
        "character_id": character_id,
        "character_name": character["name"],
        "character": character,
        "corp_history": corp_history,
        "shortend_corp_hist": shortend_corp_hist,
        "clone_list": clone_list,
        "clearance_level": get_clearance_level(request)
    })

@check_tokens()
def sni(request, character_id):
    """
    Will display the SNI details for a character
    """

    #Get data from SNI backend
    url = f"{GLOBAL_URL}/{character_id}"
    request_sni = requests.get(url, headers=global_headers(request))
    if request_sni.status_code != 200:
        return render_error(request_sni)
    
    character = request_sni.json()
    print(character)

    # Get corporation details
    if (character["corporation"] != 0):
        corp_id = character["corporation"]
        try:
            corp_name = CorporationName.objects.get(corporation_id=corp_id).corporation_name
        except CorporationName.DoesNotExist:
            corp_name_request = esi.post_universe_names(corp_id)
            corp_name = corp_name_request.json()[0]["name"]
            db_entry = CorporationName(corporation_id=corp_id, corporation_name=corp_name)
            db_entry.save()
        
        character["corporation"] = {
            "id": character["corporation"],
            "name": corp_name
        }
    else:
        character["corporation"] = {"name": ""}

    # Get alliance details
    if (character["alliance"] != 0):
        alliance_name_request = esi.post_universe_names(character["alliance"])
        character["alliance"] = {
            "id": character["alliance"],
            "name": alliance_name_request.json()[0]["name"]
        }
    else:
        character["alliance"] = {"name": ""}

    # Get coalition details
    resolved_coalition = list()
    if character["coalitions"]:
        for coalition in character["coalitions"]:
            url_coalition = f"{SNI_URL}coalition/{coalition}"
            request_coalition = requests.get(url_coalition, headers=global_headers(request))
            resolved_coalition.append({
                "id": coalition,
                "name": request_coalition.json()["coalition_name"]
            })

            #character["coalitions"][coalition] = request_coalition.json()["coalition_name"]
    character["coalitions"] = resolved_coalition

    return render(request, 'character/sni.html', {
        "character_id": character_id,
        "character_name": character["character_name"],
        "character": character,
    })

@check_tokens()
def assets(request, character_id):
    """
    Displays character assets
    """

    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    return render(request, 'character/assets.html', {
        "character": request_name.json(),
        "character_id": character_id,
    })

@check_tokens()
def contracts(request, character_id):
    """
    Displays character contracts
    """

    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    return render(request, 'character/contracts.html', {
        "character": request_name.json(),
        "character_id": character_id,
    })

@check_tokens()
def mails(request, character_id):
    """
    Displays character mails
    """

    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    return render(request, 'character/mails.html', {
        "character": request_name.json(),
        "character_id": character_id,
    })

@check_tokens()
def skills(request, character_id):
    """
    Displays character skils
    """

    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    return render(request, 'character/skills.html', {
        "character": request_name.json(),
        "character_id": character_id,
    })

@check_tokens()
def wallet(request, character_id):
    """
    Displays character wallet
    """

    request_name = esi.get_character_information(character_id)
    if request_name.status_code != 200:
        return render_error(request_name)

    return render(request, 'character/wallet.html', {
        "character": request_name.json(),
        "character_id": character_id,
    })
