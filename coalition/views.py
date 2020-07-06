from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views.defaults import bad_request

from utils import SNI_URL, SNI_DYNAMIC_TOKEN, SNI_TEMP_USER_TOKEN

import datetime
import requests

def home(request):
  """
  Will display all the coalitions registered on the SNI
  """

  url = SNI_URL + "coalition"
  headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {SNI_TEMP_USER_TOKEN}"
  }

  request_coalitions = requests.get(url, headers=headers)

  if request_coalitions.status_code == 200:
    coalition_list = request_coalitions.json()
    print(coalition_list)
    coalition_dict = {}

    for coalition in coalition_list:
      request_coalition_details = requests.get(f"{url}/{coalition['coalition_id']}", headers=headers)

      if request_coalition_details.status_code == 200:
        coalition_details = request_coalition_details.json()
        coalition_dict[coalition['coalition_id']] = coalition_details
      else:
        return HttpResponse(f"""
        ERROR {request_coalition_details.status_code} <br>
        {request_coalition_details.json()}""")

    return render(request, 'coalition/home.html', {"coalition_list": coalition_dict})
  else:
    return HttpResponse(f"""
    ERROR {request_coalitions.status_code} <br>
    {request_coalitions.json()}""")

def sheet(request, coalition_id):
    """
    Will display the main page for accessing coalition informations
    """

    url = SNI_URL + f"coalition/{coalition_id}"
    headers = {
      "accept": "application/json",
      "Authorization": f"Bearer {SNI_TEMP_USER_TOKEN}"
    }

    request_coalition = requests.get(url, headers=headers)
    if request_coalition.status_code != 200:
      return HttpResponse(f"""
      ERROR {request_coalitions.status_code} <br>
      {request_coalitions.json()}""")

    print(request_coalition.json())

    return render(request, 'coalition/sheet.html', {
        "coalition": request_coalition.json()
    })