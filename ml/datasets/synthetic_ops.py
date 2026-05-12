from ml.datasets.manifest import DatasetManifestEntry


def build_variant_plan(entry: DatasetManifestEntry) -> list[str]:
    base_plan = [
        "amount_edit",
        "date_time_edit",
        "reference_edit",
        "compression_variant",
        "crop_variant",
    ]
    if entry.label == "receipt_pdf_render":
        return [operation for operation in base_plan if operation != "crop_variant"]
    return base_plan
