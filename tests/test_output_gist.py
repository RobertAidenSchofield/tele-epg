import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.output.gist import upload_epg_to_gist, _last_uploaded_hashes


def test_gist_upload_deduplication(tmp_path):
    epg_file = tmp_path / "epg.xml"
    epg_file.write_text("<tv><channel id='1'/></tv>", encoding="utf-8")

    token = "fake_token"
    gist_id = "fake_gist_123"

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("requests.patch", return_value=mock_response) as mock_patch:
        # First upload: should call requests.patch
        success_first = upload_epg_to_gist(token, gist_id, str(epg_file))
        assert success_first is True
        assert mock_patch.call_count == 1

        # Second upload with identical content: should skip requests.patch
        success_second = upload_epg_to_gist(token, gist_id, str(epg_file))
        assert success_second is True
        assert mock_patch.call_count == 1  # Not called again

        # Modify file: should call requests.patch again
        epg_file.write_text("<tv><channel id='1'/><programme/></tv>", encoding="utf-8")
        success_third = upload_epg_to_gist(token, gist_id, str(epg_file))
        assert success_third is True
        assert mock_patch.call_count == 2

