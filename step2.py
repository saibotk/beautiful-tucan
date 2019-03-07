import collections, itertools, json, datetime, locale, re
import bs4, pystache
from bs4.element import Tag as Bs4Tag

import utils

def main():
    now     = datetime.datetime.today() # datetime.datetime(2018, 9, 5)
    today   = now.strftime("%Y-%m")
    today2  = now.strftime("%d. %b %Y")
    today4  = utils.half_semester(now)
    prefix  = "cache/" + utils.half_semester_filename(now) + "-"
    oprefix = utils.half_semester_filename(now)

    pflicht = utils.json_read(prefix + "pre-tucan-pflicht.json")
    fields  = utils.json_read(prefix + "inferno.json")
    #nebenfach = utils.json_read("nebenfach.json")

#    back = utils.groupby(((course, major +" · "+ category)
#            for major,v in nebenfach.items()
#            for category,v in v.items()
#            for module in v
#            for course in module), key=lambda x:x[0])
#    back = {k:["Y Nebenfach · " + " &<br> ".join(i[1] for i in v),""] for k,v in back}
#    fields = [back] + list(fields.values())
#    print(json.dumps(fields, indent=2))

    with open("page.html") as f: page_tmpl = f.read()
    with open("index.html") as f: index_tmpl = f.read()

    filename = lambda reg: "".join(c for c in reg if c.isalnum())

    regulations = [(k,
                    k.replace("B.Sc.", "Bachelor")
                     .replace("M.Sc.", "Master")
                     .replace(" (2015)", ""),
                    oprefix + "-" + filename(k) + ".html")
                   for k in fields.keys()
                   if k.endswith(" (2015)")]
    simple_regulations = [(a,b,c) for a,b,c in regulations if b.endswith(" Informatik")]
    hard_regulations   = [(a,b,c) for a,b,c in regulations if not b.endswith(" Informatik")]

    with open("gh-pages/index.html", "w") as f:
      f.write(pystache.render(index_tmpl, {
        "list": [
          {'href': href, 'title': today4 +" "+ regulation_short}
          for regulation, regulation_short, href in simple_regulations
        ],
        "experimentallist": [
          {'href': href, 'title': today4 +" "+ regulation_short}
          for regulation, regulation_short, href in hard_regulations
        ],
      }))

    for regulation, regulation_short, href in regulations:
        dates = utils.json_read(prefix + "-" + filename(regulation) + ".json")
        data = [clean(module_id, module, fields, regulation)
                for module_id, module in dates.items()]
        data.sort(key=lambda x:(x['category'], x['id'])) # -int(x['credits'])
        with open("style.css") as f: css_style = f.read()
        js_data = json.dumps(data, indent=" ")

        with open("gh-pages/" + href, "w") as f:
            f.write(pystache.render(page_tmpl, {
                "today":  today,
                "today2": today2,
                "today4": today4,
                "regulation_short": regulation_short,

                "js_data": js_data,
                "css_style": css_style,
            }))


def clean(module_id, entry, fields, regulation):
    def get_first(title: str, entry=entry):
        tmp = [detail for detail in entry["details"] if detail["title"] == title]
        return tmp[0].get('details') if len(tmp)>0 else None

    def get_abbr(title):
      # choose the best one of three abbreviations
      abbr1 = "".join(i for i in title if i.isupper() or i.isnumeric())
      abbr2 = "".join(i[0] if len(i)>0 else "" for i in title.strip().split(" "))
      abbr3 = (get_first("Anzeige im Stundenplan") or "").strip()
      abbrs = ( [abbr3, abbr1, abbr2]
                if 1 < len(abbr3) < 6 else
                sorted((i for i in (abbr1, abbr2)), key=lambda x: abs(3.6 - len(x))) )
      return abbrs[0]

    # module_id, title, abbr
    sort_title = entry['content'][0]['title'][10:]
    sort, title = sort_title.split(" ", 1)
    title = title or get_first("Titel") or ""
    module_id = module_id or get_first("TUCaN-Nummer") or ""
    title = utils.remove_bracketed_part(title)
    title = utils.remove_bracketed_part(title)
    title = utils.roman_to_latin_numbers(title)
    title = title.replace("Praktikum in der Lehre - ", "")
    abbr = get_abbr(title)

    # reorder details
    later_titles = {
        #"Unterrichtssprache", "Sprache",
        "Min. | Max. Teilnehmerzahl",

        "TUCaN-Nummer", "Kürzel", "Anzeige im Stundenplan", # "Titel",
        "Lehrveranstaltungsart", "Veranstaltungsart",
        "Turnus", "Startsemester",
        "SWS", "Semesterwochenstunden",
        "Diploma Supplement",
        "Modulausschlüsse", "Modulvoraussetzungen",
        "Studiengangsordnungen", "Verwendbarkeit", "Anrechenbar für",
        "Orga-Einheit", "Gebiet", "Fach",
        "Modulverantwortliche", # "Lehrende",

        "Dauer",
        "Anzahl Wahlkurse",
        "Notenverbesserung nach §25 (2)",
        "Wahlmöglichkeiten",
        "Credits",
        "Kurstermine",
    }
    early = [i for i in entry["details"] if i["title"] not in later_titles]
    late  = [i for i in entry["details"] if i["title"] in later_titles]
    entry["details"] = (
        early
      + [{"details":"<br><hr><b>Andere Angaben aus Tucan und Inferno</b><br>", "title":""}]
      + late
    )
    for detail in entry["details"]:
        if detail["details"].strip() != "":
            detail["details"] += "<br>"
        if detail['title'] == "Studiengangsordnungen":
            regs = [(x.split("(", 1))
              for x in sorted(detail['details'].replace("<br>", "<br/>").split("<br/>"))
              if x.strip()]
            regs = utils.groupby(regs, key=lambda x:x[0])
            regs = [(k,list(v)) for k,v in regs]
#            print(detail['details'].replace("<br>", "<br/>").split("<br/>"))
#            print([ k +"("+ ", ".join(i[:-1] for _,i in v) + ")" for k,v in regs])
            detail['details'] = "<br/>".join(k+"("+", ".join(i[:-1] for _,i in sorted(v))+")" for k,v in regs) + "<br/>"

    # last name of owners
    owner = "; ".join(collections.OrderedDict(
      (x,1) for entry in entry['content']
            for x in (get_first("Lehrende", entry) or
                      get_first("Modulverantwortlicher", entry) or "???").split("; ")
    ).keys()) or "???"
    short_owner = "; ".join(i.split()[-1] for i in owner.split("; "))

    # category
    isos = entry['content'][0]['title'].split(" ")[0].endswith("-os")
    category = fields[regulation].get(module_id, ["",""])[0]
    category = clean_category(category)
    if category == "C. Fachübergreifende Lehrveranstaltungen": category = ""
    category = (
      "B. Oberseminare" if isos else # category == "B. Seminare" and entry["credits"] == 0
      category or {
        "01": "C. Nebenfach FB 01 (Wirtschaft & Recht; Entrepeneurship)",
        "02": "C. Nebenfach FB 02 (Philosophie)",
        "03": "C. Nebenfach FB 03 (Humanw.; Sportw.)",
        "04": "C. Nebenfach FB 04 (Logik; Numerik; Optimierung; Stochastik)",
        "05": "C. Nebenfach FB 05 (Elektrow.; Physik)",
        "11": "C. Nebenfach FB 11 (Geow.)",
        "13": "C. Nebenfach FB 13 (Bauinformatik; Verkehr)",
        "16": "C. Nebenfach FB 16 (Fahrzeugtechnik)",
        "18": "C. Nebenfach FB 18 (Elektrotechnik)",
        "41": "C. Sprachkurse",
      }.get(module_id[:2], "0. Pflichtveranstaltungen")
    )
    if "B.Sc." in regulation:
      category = category.replace("Nebenfach", "Fachübergreifend")

    # dates
    dates   = {i for item in entry['content'] for i in item.get('dates',   [])}
    uedates = {i for item in entry['content'] for i in item.get('uedates', [])}
    uebung  = "Übung" if len(uedates) != 1 else "Übungsstunde"
    dates |= set("\t".join(y.split("\t")[:-1])+"\t"+uebung+"\t"+str(i)
                 for i in range(15) for y in uedates)
    uedates = list(uedates)
    dates = clean_dates(dates)

    # result
    result = utils.merge_dict(entry, dates)
    result = utils.merge_dict(result, {
        "id": module_id, "uedates": uedates,
        "title": title, "title_short": abbr,
        "owner": owner, "owner_short": short_owner,
        "credits": str(entry["credits"]).zfill(2),
        'category': category,
    })
    return result


def clean_category(path):
    replacements = [
        # PO 2009
        ("Grundstudium", "Pflicht"),
        ("Kanonikfächer \| Kanonische Einführungsveranstaltungen", "Pflicht"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich A", "Wahl-A"),
        ("Wahlpflichtbereich \| Wahlpflichtbereich B", "Wahl-B"),
        ("Projekte, Projektpraktika und ähnliche Veranstaltungen", "B. Praktika"),
        (" \| [^ ]* Prüfungsleistungen", ""),
        (" \| [^|]* \| ([A-Z]*) Studienleistungen \| \\1 (.*)$", " | \\2 /// \\1 "),
        # PO 2015
        ("Pflichtbereich", "BSc Pflicht"),
        ("Wahlbereich \| Studienleistungen", "BSc Wahl"),
        ("Vorgezogene Masterleistungen \| Vorgezogene Masterleistungen der Informatik \|", "MSc"),
        ("Wahlbereich Fachprüfungen", "Wahl-A"),
        ("Wahlbereich Studienleistungen", "Wahl-B"),
        (" \(sp-FB20\)", ""),
        ("Praktika, Projektpraktika, ähnliche LV", "B. Praktika"),
        ("Praktika, Projektpraktika und ähnliche Veranstaltungen", "B. Praktika"),
        ("Fachübergreifende Lehrveranstaltungen", "C. Fachübergreifende Lehrveranstaltungen"),
        ("Wahlbereiche \| ", ""),
        # common
        ("Praktika in der Lehre", "B. Praktika in der Lehre"),
        ("Praktikum in der Lehre", "B. Praktika in der Lehre"),
        ("Module der ", ""),
        ("Fachübergreifend \| Gesamtkatalog aller Module des Sprachenzentrums", "Sprachzentrum"),
        (" \| ([^|]*) \| \\1", " | \\1 "),
        ("Projektpraktika", "X Praktika"),
        ("Projekte", "B. Praktika"),
        ("Seminare", "B. Seminare")
    ]
    for match, result in replacements:
        path = re.sub(match, result, path)
    if path and not path[:3] in ["A.", "B. ", "C. "]:
        path = "A. " + path
    return path


def clean_dates(item):
    def parse_date(string):
      day, start, end, room = string.split("\t", 3)
      room = room.split("\t")[0]
      day   = datetime.datetime.strptime(day, "%Y-%m-%d")
      start = utils.parse_hm(start)
      end   = utils.parse_hm(end)
      return [day, start, end, room]

    dates = list(sorted(parse_date(i) for i in item))

    # first, last event
    first = last = first_to_last = ""
    if len(dates) > 0:
        first = dates[ 0][0].strftime("%Y-%m-%d")
        last  = dates[-1][0].strftime("%Y-%m-%d")
        first_to_last = "Termine liegen von %s bis %s:<br>" % (
            dates[ 0][0].strftime("%d. %b"),
            dates[-1][0].strftime("%d. %b"),
        )

    # how many weeks does the event repeat?
    counted = collections.Counter( (i[0].weekday(), i[1], i[2]) for i in dates )
    counted = [{"count": count, "day": v[0], "start": v[1], "end": v[2]}
              for v, count in counted.items()]

    # add rooms of weekly events together
    for d in counted:
        roomlst = [room for i in dates
                        if (i[0].weekday(), i[1], i[2]) == (d['day'], d['start'], d['end'])
                        for room in i[3].split(",")]
        d['room'] = ", ".join(set(roomlst))

    counted.sort(key=lambda a: (-a["count"], a["day"]))
    return {
        "dates": [(i[0].strftime("%Y-%m-%d"), i[1:]) for i in dates], "weekly": counted,
        "first_to_last": first_to_last, "first": first, "last": last,
    }

if __name__ == "__main__": main()

