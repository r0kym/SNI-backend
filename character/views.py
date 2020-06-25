from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views.defaults import bad_request

from SNI.esi import post_universe_names

# Create your views here.

def home(request, character_id):
    """
    Will display the main page for accessing charachter informations
    """

    request_name = post_universe_names(character_id)
    print(request_name.json())
    if request_name.status_code == 200:
        if request_name.json()[0]["category"] == "character":
            character_name = request_name.json()[0]["name"]
        else:
            raise Http404("Not a character id")
    else:
        raise Http404(request_name.json()["error"])

    return render(request, 'character/home.html', {"character_id":character_id, "character_name": character_name})