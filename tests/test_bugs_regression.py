import pytest
from vieneu.factory import Vieneu
from vieneu.turbo import TurboVieNeuTTS
from unittest.mock import MagicMock, patch
import numpy as np

def test_vieneu_factory_invalid_mode():
    with pytest.raises(ValueError, match="Unknown mode 'invalid_mode'"):
        Vieneu(mode="invalid_mode")

@patch("vieneu.turbo.phonemize_batch")
def test_turbo_infer_batch_uses_prephonemized(mock_phonemize_batch):
    # Setup mock
    mock_phonemize_batch.return_value = ["ph1", "ph2"]

    # Mocking dependencies for TurboVieNeuTTS
    with patch("vieneu.turbo.TurboVieNeuTTS._load_backbone"), \
         patch("vieneu.turbo.BaseTurboVieNeuTTS._load_decoder"), \
         patch("vieneu.turbo.BaseTurboVieNeuTTS._load_encoder"), \
         patch("vieneu.turbo.BaseTurboVieNeuTTS._load_voices"), \
         patch("vieneu.turbo.normalize_device"):

        tts = TurboVieNeuTTS(backbone_repo="dummy", device="cpu")
        tts.infer = MagicMock(return_value=np.zeros(100))
        tts.get_preset_voice = MagicMock(return_value={"codes": [0]*128})

        texts = ["text1", "text2"]
        tts.infer_batch(texts, apply_watermark=False)

        # Verify phonemize_batch was called
        mock_phonemize_batch.assert_called_once()

        # Verify infer was called with phonemes and skip_phonemize=True
        assert tts.infer.call_count == 2

        # Check that infer was called with the phonemes "ph1" and "ph2"
        # and that skip_phonemize=True was passed.
        calls = tts.infer.call_args_list
        assert calls[0][0][0] == "ph1"
        assert calls[0][1]["skip_phonemize"] is True
        assert calls[1][0][0] == "ph2"
        assert calls[1][1]["skip_phonemize"] is True
