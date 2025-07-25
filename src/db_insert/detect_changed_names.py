import psycopg2
from dotenv import load_dotenv
import os

from utils.gpt_name_formatter import cannonicalize_name, format_name_basic


load_dotenv()

if __name__ == "__main__":
    if os.getenv("DATABASE_URL") is None:
        print("Make sure to specify DATABASE_URL in .env file")
        exit(1)

    print(f"Connecting to database at '{os.getenv('DB_FILE')}'")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    # Load existing entries
    cur.execute("SELECT cod_siiir_unitate, denumire_lunga_unitate, judet_pj FROM siiir")
    existing = cur.fetchall()
    siiir_dict = {row[0]: row for row in existing}

    # Load existing entries
    cur.execute("SELECT cod_siiir, nume, cod_judet FROM institutii")
    institutii = cur.fetchall()

    print(f"Loaded {len(institutii)} existing institutii")

    found = 0
    differences = 0
    for siiir, nume, cod_judet in institutii:
        if siiir not in siiir_dict:
            print(
                f"Missing school '{nume}' with SIIIR code {siiir} and county code {cod_judet}\n"
            )
            # cur.execute(
            #     "INSERT INTO siiir (cod_siiir, denumire_lunga_unitate, cod_judet) VALUES (%s, %s, %s)",
            #     (siiir, nume, cod_judet),
            # )
            # print(f"Inserted {nume} into siiir")
            # print()
        else:
            siiir_name = siiir_dict[siiir][1]
            siiir_cod_judet = siiir_dict[siiir][2]

            cname_new = (
                cannonicalize_name(nume, cod_judet, id=True)
                .replace("_", "")
                .replace("A", "I")
            )
            cname_old = (
                cannonicalize_name(siiir_name, siiir_cod_judet, id=True)
                .replace("_", "")
                .replace("A", "I")
            )
            if cname_new != cname_old:
                print(
                    f"Found different name '{nume}' for siiir school '{siiir_name}', SIIIR code {siiir}"
                )
                print(f"{cname_new} != {cname_old}")
                differences += 1

                new_name = format_name_basic(siiir_name)
                print(f"Setting new name: {new_name}")
                print("")
                # cur.execute(
                #     "UPDATE institutii SET nume = %s WHERE cod_siiir = %s",
                #     (new_name, siiir),
                # )
                # conn.commit()

                # if differences > 10:
                #     exit()
            found += 1

    print(f"Found {found} existing schools")
    print(f"Found {differences} differences")

    # conn.commit()
    conn.close()
