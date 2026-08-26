"""Realistic reference data for generating shipments."""

# Ports — UN/LOCODE
INDIAN_PORTS = [
    ("INNSA", "Nhava Sheva"),
    ("INMUN", "Mundra"),
    ("INMAA", "Chennai"),
    ("INCOK", "Cochin"),
]

AUSTRALIAN_PORTS = [
    ("AUSYD", "Sydney"),
    ("AUMEL", "Melbourne"),
    ("AUBNE", "Brisbane"),
    ("AUFRE", "Fremantle"),
]

# Vessels — name, IMO (real-format 7 digits)
VESSELS = [
    ("MAERSK KALAMATA", "9784271"),
    ("MSC RITA", "9484469"),
    ("CMA CGM CENDRILLON", "9410046"),
    ("ANL WYONG", "9463855"),
    ("OOCL BRISBANE", "9622889"),
]

CONTAINER_PREFIXES = ["MSCU", "MAEU", "CMAU", "OOLU", "TGHU", "GESU"]

# Goods — description, hs_code, material, unit_price_range, weight_per_unit_kg
PRODUCTS = [
    ("Men's T-Shirts, 100% Cotton, Knitted", "6109.10", "cotton", (8, 24), 0.18),
    ("Ladies Blouses, Woven Polyester", "6206.40", "polyester", (12, 32), 0.15),
    ("Cotton Bed Sheets, Printed", "6302.21", "cotton", (15, 40), 0.60),
    ("Leather Handbags", "4202.21", "leather", (35, 120), 0.85),
    ("Stainless Steel Kitchenware", "7323.93", "steel", (6, 28), 1.20),
    ("Ceramic Tableware, Porcelain", "6911.10", "ceramic", (4, 18), 0.90),
    ("Rubber Floor Mats", "4016.91", "rubber", (9, 26), 2.10),
    ("Wooden Photo Frames", "4414.90", "wood", (5, 22), 0.55),
    ("Brass Decorative Items", "8306.29", "brass", (14, 55), 1.40),
    ("Cotton Bath Towels", "6302.60", "cotton", (10, 30), 0.45),
]

INDIAN_EXPORTERS = [
    ("Rajesh Textiles Pvt Ltd", "Andheri East", "Mumbai", "400059"),
    ("Coromandel Exports Ltd", "Guindy Industrial Estate", "Chennai", "600032"),
    ("Gujarat Handicrafts Co", "GIDC Phase II", "Ahmedabad", "382445"),
    ("Punjab Cotton Mills", "Focal Point", "Ludhiana", "141010"),
    ("Kerala Spice Traders", "Willingdon Island", "Cochin", "682003"),
]

AUSTRALIAN_IMPORTERS = [
    ("Coastline Apparel Pty Ltd", "12 Bourke Street", "Sydney", "2000"),
    ("Southern Cross Homewares", "88 Collins Street", "Melbourne", "3000"),
    ("Harbour Retail Group", "45 Queen Street", "Brisbane", "4000"),
    ("Westline Trading Pty Ltd", "220 St Georges Tce", "Perth", "6000"),
]

CHAMBERS_OF_COMMERCE = [
    "Bombay Chamber of Commerce and Industry",
    "Federation of Indian Export Organisations",
    "Madras Chamber of Commerce and Industry",
]

FUMIGATION_COMPANIES = [
    "Pest Control (India) Pvt Ltd",
    "Bharat Fumigation Services",
    "Anchor Pest Solutions",
]

PACKAGE_TYPES = ["CARTON", "PALLET", "CRATE", "BALE"]

CONTAINER_SIZES = [
    ("20GP", 2230),
    ("40GP", 3750),
    ("40HC", 3900),
]