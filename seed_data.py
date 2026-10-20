"""Master data: foods (nutrition per 100 g) and exercises (MET values).

Values are approximate averages for common foods, good enough for a student project.
Tuple format: (name, category, serving_g, kcal/100g, protein, carbs, fat)
"""

FOODS = [
    # Grains & staples
    ("Roti (wheat)",        "Grains",     40,  297, 9.8, 55.0, 3.7),
    ("Rice (cooked)",       "Grains",    150,  130, 2.7, 28.0, 0.3),
    ("Brown rice (cooked)", "Grains",    150,  112, 2.6, 23.0, 0.9),
    ("Oats (dry)",          "Grains",     40,  389, 16.9, 66.0, 6.9),
    ("Poha",                "Grains",    150,  130, 2.5, 26.0, 1.5),
    ("Idli",                "Grains",     40,  146, 4.5, 30.0, 0.6),
    ("Dosa (plain)",        "Grains",     80,  168, 3.9, 29.0, 3.7),
    ("Upma",                "Grains",    150,  150, 3.5, 22.0, 5.0),
    ("Bread (brown)",       "Grains",     30,  247, 9.0, 41.0, 3.4),
    # Proteins
    ("Dal (cooked)",        "Protein",   150,  116, 9.0, 20.0, 0.4),
    ("Rajma (cooked)",      "Protein",   150,  127, 8.7, 22.8, 0.5),
    ("Chana (cooked)",      "Protein",   150,  164, 8.9, 27.4, 2.6),
    ("Paneer",              "Protein",   100,  265, 18.3, 1.2, 20.8),
    ("Tofu",                "Protein",   100,   76, 8.0, 1.9, 4.8),
    ("Egg (boiled)",        "Protein",    50,  155, 13.0, 1.1, 11.0),
    ("Egg whites",          "Protein",    99,   52, 11.0, 0.7, 0.2),
    ("Chicken breast",      "Protein",   120,  165, 31.0, 0.0, 3.6),
    ("Fish (rohu)",         "Protein",   120,   97, 16.6, 0.0, 2.6),
    ("Soya chunks (dry)",   "Protein",    30,  345, 52.0, 33.0, 0.5),
    ("Sprouts (moong)",     "Protein",   100,   30, 3.0, 5.9, 0.2),
    ("Whey protein",        "Protein",    30,  400, 80.0, 8.0, 6.0),
    # Dairy
    ("Milk (toned)",        "Dairy",     250,   58, 3.1, 4.7, 3.0),
    ("Curd",                "Dairy",     150,   60, 3.5, 4.7, 3.1),
    ("Greek yogurt",        "Dairy",     150,   59, 10.0, 3.6, 0.4),
    # Fruits & veg
    ("Banana",              "Fruit",     120,   89, 1.1, 22.8, 0.3),
    ("Apple",               "Fruit",     150,   52, 0.3, 13.8, 0.2),
    ("Papaya",              "Fruit",     150,   43, 0.5, 10.8, 0.3),
    ("Mixed veg sabzi",     "Vegetable", 150,   85, 2.5, 10.0, 4.0),
    ("Salad (cucumber/tomato)", "Vegetable", 150, 18, 0.8, 3.7, 0.2),
    ("Palak (cooked)",      "Vegetable", 150,   41, 3.0, 4.0, 1.5),
    # Snacks & others
    ("Peanuts (roasted)",   "Snack",      30,  567, 25.8, 16.1, 49.2),
    ("Almonds",             "Snack",      20,  579, 21.2, 21.6, 49.9),
    ("Roasted chana",       "Snack",      30,  369, 22.0, 58.0, 5.0),
    ("Samosa",              "Snack",      80,  262, 3.5, 24.0, 17.0),
    ("Biscuits",            "Snack",      30,  480, 6.5, 70.0, 20.0),
    ("Maggi noodles",       "Snack",      70,  427, 8.5, 60.0, 17.0),
    ("Tea with sugar",      "Beverage",  150,   40, 1.0, 7.0, 1.0),
    ("Cold drink",          "Beverage",  300,   42, 0.0, 10.6, 0.0),
]

# (name, MET value) — from the Compendium of Physical Activities
EXERCISES = [
    ("Walking (moderate)", 3.5),
    ("Brisk walking",      4.3),
    ("Running (8 km/h)",   8.3),
    ("Cycling (moderate)", 7.5),
    ("Skipping rope",     12.3),
    ("Yoga",               2.5),
    ("Gym (weights)",      5.0),
    ("Swimming",           6.0),
    ("Badminton",          5.5),
    ("Football",           7.0),
    ("Cricket",            4.8),
    ("Dancing",            5.0),
]
