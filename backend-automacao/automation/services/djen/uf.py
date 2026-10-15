"""Geographic filters based on tribunal jurisdiction and CNJ process origin.

Regional tribunals spanning several UFs are never assigned to every UF they
serve. Federal cases use the section encoded in the four origin digits.
Reference: https://www.cnj.jus.br/wp-content/uploads/2011/02/trfs.pdf
"""
from django.db.models import Q

UFS = tuple("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split())
# CNJ state/electoral tribunal codes (alphabetical order by state name).
CNJ_STATES = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SE SP TO".split()
FEDERAL = {
    "AC": ("01", "30"), "AM": ("01", "31"), "AP": ("01", "32"),
    "BA": ("01", "33"), "DF": ("01", "34"), "GO": ("01", "35"),
    "MT": ("01", "36"), "MA": ("01", "37"), "MG": ("01|06", "38"),
    "PA": ("01", "39"), "PI": ("01", "40"), "RO": ("01", "41"),
    "RR": ("01", "42"), "TO": ("01", "43"),
    "ES": ("02", "50"), "RJ": ("02", "51"),
    "MS": ("03", "60|62"), "SP": ("03", "61|63"),
    "PR": ("04", "70"), "RS": ("04", "71"), "SC": ("04", "72"),
    "AL": ("05", "80"), "CE": ("05", "81"), "PB": ("05", "82"),
    "PE": ("05", "83"), "RN": ("05", "84"), "SE": ("05", "85"),
}
# Only regions whose jurisdiction is a single UF. TRT10/11/14 span UFs.
LABOUR = {
    "RJ": (1,), "SP": (2, 15), "MG": (3,), "RS": (4,), "BA": (5,),
    "PE": (6,), "CE": (7,), "PR": (9,), "SC": (12,), "PB": (13,),
    "MA": (16,), "ES": (17,), "GO": (18,), "AL": (19,), "SE": (20,),
    "RN": (21,), "PI": (22,), "MT": (23,), "MS": (24,),
}


def uf_condition(states):
    condition = Q(pk__in=[])
    for uf in states:
        aliases = [f"TJ{uf}", f"TRE{uf}", f"TRE-{uf}", f"TRE/{uf}", f"TJM{uf}", f"TJM-{uf}"]
        if uf == "DF":
            aliases.append("TJDFT")
        for region in LABOUR.get(uf, ()):
            aliases.extend((f"TRT{region}", f"TRT{region:02}", f"TRT-{region}", f"TRT-{region:02}"))
        for alias in aliases:
            condition |= Q(tribunal__iexact=alias)
        # Accept both masked and unmasked process numbers; never search text/OAB.
        code = CNJ_STATES.index(uf) + 1
        pattern = rf"^[0-9]{{7}}-?[0-9]{{2}}\.?[0-9]{{4}}\.?[689]\.?{code:02}\.?[0-9]{{4}}$"
        condition |= Q(processo__numero__regex=pattern)
        region, section = FEDERAL[uf]
        pattern = rf"^[0-9]{{7}}-?[0-9]{{2}}\.?[0-9]{{4}}\.?4\.?({region})\.?({section})[0-9]{{2}}$"
        condition |= Q(processo__numero__regex=pattern)
    return condition
