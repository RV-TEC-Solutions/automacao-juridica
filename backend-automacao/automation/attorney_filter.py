from django.conf import settings
from rest_framework.exceptions import ParseError


def attorney_param(params):
    attorney = params.get("attorney", "")
    if attorney not in ("", "murilo", "cristiano"):
        raise ParseError("Advogado inválido.")
    return attorney


def filter_djen_attorney(queryset, attorney):
    if not attorney:
        return queryset
    number = settings.DJEN_OAB_NUMBER if attorney == "murilo" else settings.DJEN_CRISTIANO_OAB_NUMBER
    state = settings.DJEN_OAB_STATE if attorney == "murilo" else settings.DJEN_CRISTIANO_OAB_STATE
    if not number or not state:
        return queryset.none()
    return queryset.filter(attorneys__oab_number__iexact=str(number).strip(), attorneys__oab_state__iexact=state.strip())
