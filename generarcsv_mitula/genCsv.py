import boto3
import csv
import io
from bs4 import BeautifulSoup


def lambda_handler(event, context):
    """
    Se dispara al subirse 'ready.txt' a 'dlandingcasas-mitula'.
    Procesa todos los .html y genera un CSV en 'rlandingcasas-mitula'.
    Luego, borra el 'ready.txt' para evitar re-disparar la Lambda.
    """

    s3 = boto3.client('s3')

    record = event['Records'][0]
    source_bucket = record['s3']['bucket']['name']
    source_key = record['s3']['object']['key']

    if source_key != "ready.txt":
        print(f"[INFO] No es 'ready.txt'. Se ignora: {source_key}")
        return {
            "statusCode": 200,
            "body": "Archivo no es ready.txt"
        }

    # Listar .html
    response = s3.list_objects_v2(Bucket=source_bucket)
    contents = response.get("Contents", [])
    html_keys = [
        obj["Key"]
        for obj in contents
        if obj["Key"].endswith(".html")
    ]

    print(
        f"[INFO] Se encontraron {len(html_keys)} archivos .html "
        "para procesar."
    )

    all_rows = []
    header = [
        "FechaDescarga",
        "Barrio",
        "Valor",
        "NumHabitaciones",
        "NumBanos",
        "mts2",
    ]
    all_rows.append(header)

    for key in html_keys:
        html_obj = s3.get_object(Bucket=source_bucket, Key=key)
        html_content = html_obj["Body"].read().decode("utf-8")

        soup = BeautifulSoup(html_content, "html.parser")
        listings = soup.find_all("div", class_="listing")

        fecha_descarga = key.replace(".html", "")

        for listing in listings:
            barrio = (
                listing.find("span", class_="barrio").get_text(strip=True)
                if listing.find("span", class_="barrio")
                else ""
            )
            valor = (
                listing.find("span", class_="valor").get_text(strip=True)
                if listing.find("span", class_="valor")
                else ""
            )
            habs = (
                listing.find("span", class_="habs").get_text(strip=True)
                if listing.find("span", class_="habitaciones")
                else ""
            )
            banos = (
                listing.find("span", class_="banos").get_text(strip=True)
                if listing.find("span", class_="banos")
                else ""
            )
            mts2 = (
                listing.find("span", class_="mts2").get_text(strip=True)
                if listing.find("span", class_="mts2")
                else ""
            )

            all_rows.append([
                fecha_descarga,
                barrio,
                valor,
                habs,
                banos,
                mts2,
            ])

    # Generar CSV
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerows(all_rows)

    final_bucket = "rlandingcasas-mitula"
    final_key = "batch.csv"

    s3.put_object(
        Bucket=final_bucket,
        Key=final_key,
        Body=csv_buffer.getvalue(),
        ContentType="text/csv",
    )
    print(
        f"[INFO] CSV '{final_key}' creado con {len(html_keys)} archivos "
        f"en '{final_bucket}'."
    )

    # Borrar 'ready.txt' para no re-disparar la Lambda
    s3.delete_object(Bucket=source_bucket, Key="ready.txt")
    print("[INFO] 'ready.txt' eliminado tras procesar .html.")

    return {
        "statusCode": 200,
        "body": (
            f"CSV '{final_key}' generado y 'ready.txt' borrado. "
            f"Procesados {len(html_keys)} archivos."
        )
    }
