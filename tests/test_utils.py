from src.twojtenis_mcp.utils import extract_id_from_url


def test_extract_id_from_image_url():
    id = extract_id_from_url("/www/clubs/emblems/90.png")
    assert id == "90"


def test_extract_id_from_html_url():
    id = extract_id_from_url("/pl/rsv/show/69184bbcb7df0.html")
    assert id == "69184bbcb7df0"
