import re
import psycopg2
import unidecode
from Levenshtein import ratio, distance

from utils.gpt_name_formatter import cannonicalize_name
from utils.parsing import fix_name_encoding

institutions_table_name = "public.institutii"
siiir_table_name = "public.siiir"


def cannonical_id_from_name(name, cod_judet):
    cname = cannonicalize_name(name, cod_judet, id=True)
    cname = cname[:-1-len(cod_judet)]  # Remove county code
    cname = cod_judet + '_' + cname  # Add county code at the beginning
    # Increase digit importance
    for i in range(10):
        cname = cname.replace(str(i), str(i) * 10)
    cname = fix_name_encoding(cname)
    return cname

    # Remove underscores
    name = name.replace("_", " ")

    # Remove non-alphanumeric characters
    name = unidecode.unidecode(name)
    name = re.sub(r"[^a-zA-Z0-9 ]+", " ", name)

    # Add county name
    name = cod_judet + " " + name

    # Convert to uppercase
    name = name.upper()

    # Fix whitespaces
    name = re.sub(r" +", " ", name)
    name = name.strip()

    # Replace spaces with underscores
    name = name.replace(" ", "_")

    # Increase digit importance
    for i in range(10):
        name = name.replace(str(i), str(i) * 10)

    return name


matching = None


def compute_siiir_matching(source_schools, db_url, gimnaziu=False):

    if db_url is None:
        print("Make sure to specify DATABASE_URL in .env file")
        exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    global matching
    matching = {}  # {name: code}

    unmatched_sources = []  # [(name, cod_judet)]
    unmatched_targets = {}  # {cod_judet: {code: [names]}}

    unmatched_targets_by_name = {}  # {cod_judet: {name: code}}

    cur.execute(f"SELECT cod_judet, cod_siiir, nume FROM {institutions_table_name}")
    for cod_judet, cod_siiir, name in cur.fetchall():
        if cod_judet not in unmatched_targets:
            unmatched_targets[cod_judet] = {}
            unmatched_targets_by_name[cod_judet] = {}
        name = cannonical_id_from_name(name, cod_judet)
        unmatched_targets[cod_judet][cod_siiir] = [name]
        unmatched_targets_by_name[cod_judet][name] = cod_siiir

    # Load target schools from database
    cur.execute(
        f"SELECT denumire_lunga_unitate, judet_pj, cod_siiir_unitate FROM {siiir_table_name} {"WHERE stare_liceal is not null" if not gimnaziu else ""}"
    )
    for name, cod_judet, cod_siiir in cur.fetchall():
        if cod_judet in unmatched_targets and cod_siiir in unmatched_targets[cod_judet]:
            name = cannonical_id_from_name(name, cod_judet)
            unmatched_targets[cod_judet][cod_siiir].append(name)

    # Exact matches
    for name, cod_judet in source_schools:
        name = cannonical_id_from_name(name, cod_judet)
        # code = unmatched_targets.get(cod_judet, {}).get(name, None)
        code = unmatched_targets_by_name.get(cod_judet, {}).get(name, None)
        if code is not None and code in unmatched_targets[cod_judet]:
            matching[name] = code
            unmatched_targets[cod_judet].pop(code)
        else:
            unmatched_sources.append((name, cod_judet))

    # Levenshtein matches
    max_ratios = [0.1, 0.2, 0.3, 0.4] if not gimnaziu else [0.0]
    for max_ratio in max_ratios:
        for s_name, s_judet in unmatched_sources[:]:
            if len(unmatched_targets[s_judet]) == 0:
                continue

            best_match = min(
                unmatched_targets[s_judet],
                key=lambda x: min(
                    distance(s_name, y) for y in unmatched_targets[s_judet][x]
                ),
            )
            best_distance = min(
                distance(s_name, y) for y in unmatched_targets[s_judet][best_match]
            )

            ratio = best_distance / len(s_name)

            if ratio <= max_ratio:
                print(
                    f"Found similar school '{best_match}' for '{s_name}' with ratio {ratio:.2f} - {unmatched_targets[s_judet][best_match]}"
                )
                matching[s_name] = best_match
                unmatched_targets[s_judet].pop(best_match)
                unmatched_sources.remove((s_name, s_judet))

    print("Matched schools:" + str(len(matching)))
    print("Unmatched schools:" + str(len(unmatched_sources)))
    print(str([x[0] for x in unmatched_sources]))


def get_siiir_by_name(name, cod_judet):
    if matching is None:
        print("Please run compute_siiir_matching() first")
        exit(1)

    name = cannonical_id_from_name(name, cod_judet)
    code = matching.get(name, None)
    return code
