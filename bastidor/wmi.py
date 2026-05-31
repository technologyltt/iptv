"""Tabla WMI (World Manufacturer Identifier) local.

Permite identificar fabricante, marca y país de fabricación a partir de los
3 primeros caracteres del VIN/bastidor SIN conexión a internet. Para datos
más finos (modelo, motor, cilindrada) se complementa con la API de la NHTSA.

El estándar VIN es mundial (ISO 3779), así que esto funciona igual para un
coche español, alemán o japonés.
"""

# --- País por el primer carácter del VIN (rangos ISO 3780) ---
# (inicio, fin, país)  -- comparación alfabética sobre el 1er carácter
_COUNTRY_RANGES = [
    ("A", "C", "Sudáfrica / África"),
    ("J", "J", "Japón"),
    ("K", "K", "Corea del Sur"),
    ("L", "L", "China"),
    ("M", "M", "India / Indonesia / Tailandia"),
    ("N", "N", "Turquía"),
    ("P", "P", "Filipinas / Malasia"),
    ("R", "R", "Taiwán / Vietnam"),
    ("S", "S", "Reino Unido"),
    ("T", "T", "Suiza / Chequia / Hungría"),
    ("U", "U", "Rumanía / Eslovaquia"),
    ("V", "V", "Francia / España / Austria"),
    ("W", "W", "Alemania"),
    ("X", "X", "Rusia / Bulgaria"),
    ("Y", "Y", "Suecia / Finlandia / Bélgica"),
    ("Z", "Z", "Italia"),
    ("1", "5", "Estados Unidos / Canadá"),
    ("6", "7", "Oceanía (Australia / N. Zelanda)"),
    ("8", "9", "Sudamérica"),
    ("0", "0", "Sudamérica"),
]

# --- Marca por WMI (3 primeros caracteres). Los más comunes en Europa/España ---
_WMI = {
    # Alemania
    "WBA": "BMW", "WBS": "BMW M", "WBX": "BMW (SUV)", "WBY": "BMW i",
    "WBV": "BMW (Mini)", "WMW": "MINI",
    "WAU": "Audi", "WA1": "Audi (SUV)", "WUA": "Audi Sport", "TRU": "Audi (Hungría)",
    "WVW": "Volkswagen", "WV1": "VW Comercial", "WV2": "VW Comercial",
    "WVG": "VW (SUV)", "1VW": "Volkswagen (EE.UU.)", "3VW": "VW (México)",
    "WDB": "Mercedes-Benz", "WDD": "Mercedes-Benz", "WDC": "Mercedes-Benz (SUV)",
    "W1K": "Mercedes-Benz", "W1N": "Mercedes-Benz (SUV)", "WDF": "Mercedes Vito/Sprinter",
    "WMX": "Mercedes-AMG", "WDA": "Mercedes-Benz",
    "WP0": "Porsche", "WP1": "Porsche (SUV)",
    "WF0": "Ford (Alemania)", "WVG": "Volkswagen",
    "W0L": "Opel", "W0V": "Opel", "VSX": "Opel (España)",
    # España
    "VSS": "SEAT", "VSE": "SEAT", "VS5": "SEAT",
    "VWV": "Volkswagen Navarra", "VF7": "Citroën",
    # Francia
    "VF1": "Renault", "VF2": "Renault", "VF6": "Renault Trucks",
    "VF3": "Peugeot", "VR3": "Peugeot", "VF4": "Talbot",
    "VR7": "Citroën / DS", "VR1": "DS Automobiles",
    # Italia
    "ZFA": "Fiat", "ZFC": "Fiat", "ZFF": "Ferrari", "ZAR": "Alfa Romeo",
    "ZLA": "Lancia", "ZHW": "Lamborghini", "ZAM": "Maserati", "ZAP": "Piaggio",
    # Reino Unido
    "SAL": "Land Rover", "SAJ": "Jaguar", "SAR": "Rover", "SCC": "Lotus",
    "SCB": "Bentley", "SCA": "Rolls-Royce", "SCE": "DeLorean", "SDB": "Peugeot UK",
    "SFD": "LDV", "SJN": "Nissan UK", "SB1": "Toyota UK",
    # Chequia / Eslovaquia / Hungría
    "TMB": "Škoda", "TMP": "Škoda", "TMK": "Kia (Eslovaquia)",
    "TMA": "Hyundai (Chequia)", "TM8": "Suzuki (Hungría)", "MMM": "SsangYong",
    # Suecia
    "YV1": "Volvo", "YV4": "Volvo (SUV)", "YS3": "Saab", "YS2": "Scania",
    "YS4": "DAF (Suecia)",
    # Japón
    "JT": "Toyota", "JTD": "Toyota", "JTM": "Toyota", "JTH": "Lexus",
    "JN1": "Nissan", "JN6": "Nissan", "JN8": "Nissan", "JHM": "Honda",
    "JHL": "Honda (SUV)", "JH4": "Acura", "JM1": "Mazda", "JM3": "Mazda (SUV)",
    "JF1": "Subaru", "JF2": "Subaru (SUV)", "JS1": "Suzuki", "JS2": "Suzuki",
    "JS3": "Suzuki", "JMB": "Mitsubishi", "JMY": "Mitsubishi", "JA3": "Mitsubishi",
    "JKA": "Kawasaki", "JYA": "Yamaha",
    # Corea
    "KMH": "Hyundai", "KMF": "Hyundai (furgón)", "KM8": "Hyundai (SUV)",
    "KNA": "Kia", "KND": "Kia (SUV)", "KNE": "Kia", "KNM": "Renault Samsung",
    "KPT": "SsangYong",
    # China
    "LSV": "Volkswagen (China)", "LFV": "FAW-VW", "LVS": "Ford (China)",
    "LGB": "Dongfeng", "LB2": "Geely", "L6T": "Geely", "LRW": "Tesla (China)",
    "LJ1": "JAC", "LYV": "Volvo (China)", "LDC": "Dongfeng-PSA",
    # EE.UU.
    "1HG": "Honda (EE.UU.)", "1FA": "Ford", "1FT": "Ford (pickup)",
    "1G1": "Chevrolet", "1GC": "Chevrolet (pickup)", "1C3": "Chrysler",
    "1C4": "Jeep", "2T1": "Toyota (Canadá)", "4T1": "Toyota (EE.UU.)",
    "5YJ": "Tesla", "7SA": "Tesla", "5UX": "BMW (EE.UU.)", "4US": "BMW (EE.UU.)",
    "WBA": "BMW",
    # India
    "MAT": "Tata Motors", "MA1": "Mahindra", "MA3": "Suzuki / Maruti",
    "MBH": "Suzuki / Maruti", "MAL": "Hyundai (India)",
}

# Si el WMI exacto de 3 no está, probamos por marca según los 2 primeros
_WMI2 = {
    "WB": "BMW", "WA": "Audi", "WV": "Volkswagen", "WD": "Mercedes-Benz",
    "WP": "Porsche", "VS": "SEAT", "VF": "Grupo PSA/Renault (Francia)",
    "ZF": "Fiat", "ZA": "Alfa Romeo / Maserati", "SA": "Jaguar Land Rover",
    "TM": "Škoda / VAG (Chequia)", "YV": "Volvo", "YS": "Saab/Scania",
    "JT": "Toyota", "JN": "Nissan", "JH": "Honda", "JM": "Mazda/Mitsubishi",
    "JF": "Subaru", "JS": "Suzuki", "KM": "Hyundai", "KN": "Kia",
}


def country_from_vin(vin: str) -> str:
    if not vin:
        return "Desconocido"
    c = vin[0].upper()
    for lo, hi, name in _COUNTRY_RANGES:
        if lo <= c <= hi:
            return name
    return "Desconocido"


def brand_from_vin(vin: str) -> str | None:
    if not vin or len(vin) < 3:
        return None
    w3 = vin[:3].upper()
    if w3 in _WMI:
        return _WMI[w3]
    w2 = vin[:2].upper()
    return _WMI2.get(w2)
