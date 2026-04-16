import gradio as gr
import os
import sys
import threading
from sea_g2p import Normalizer
import apps.model_manager as model_manager
import apps.inference_runner as inference_runner
import apps.ui_builder as ui_builder
from vieneu_utils.core_utils import env_bool

# Global lock for thread safety
model_lock = threading.Lock()

# Normalizer (module-level singleton)
_text_normalizer = Normalizer()

DEFAULT_TEXT_GPU = "Hà Nội, trái tim của Việt Nam, là một thành phố ngàn năm văn hiến với bề dày lịch sử và văn hóa độc đáo. Bước chân trên những con phố cổ kính quanh Hồ Hoàn Kiếm, du khách như được du hành ngược thời gian, chiêm ngưỡng kiến trúc Pháp cổ điển hòa quyện với nét kiến trúc truyền thống Việt Nam. Mỗi con phố trong khu phố cổ mang một tên gọi đặc trưng, phản ánh nghề thủ công truyền thống từng thịnh hành nơi đây như phố Hàng Bạc, Hàng Đào, Hàng Mã. Ẩm thực Hà Nội cũng là một điểm nhấn đặc biệt, từ tô phở nóng hổi buổi sáng, bún chả thơm lừng trưa hè, đến chè Thái ngọt ngào chiều thu. Những món ăn dân dã này đã trở thành biểu tượng của văn hóa ẩm thực Việt, được cả thế giới yêu mến. Người Hà Nội nổi tiếng với tính cách hiền hòa, lịch thiệp nhưng cũng rất cầu toàn trong từng chi tiết nhỏ, từ cách pha trà sen cho đến cách chọn hoa sen tây để thưởng trà."
DEFAULT_TEXT_TURBO = (
    "Trước đây, hệ thống điện chủ yếu sử dụng direct current, nhưng Tesla đã chứng minh rằng alternating current is more efficient for long-distance transmission. Nhờ đó, điện có thể được truyền đi xa hơn với ít tổn thất năng lượng hơn. Đây là một bước tiến cực kỳ quan trọng trong ngành điện.\n\n"
    "Một trong những phát minh nổi tiếng của ông là Tesla coil, một thiết bị có thể tạo ra điện áp rất cao và những tia sét nhân tạo. This device is still used today in demonstrations và trong một số ứng dụng nghiên cứu. Khi nhìn thấy những tia điện này, nhiều người cảm thấy vừa ấn tượng vừa hơi đáng sợ."
)

def safe_load_model(*args):
    with model_lock:
        yield from model_manager.load_model(*args)

def safe_synthesize_speech(*args):
    # We don't necessarily need to lock the whole inference if the model itself is thread-safe,
    # but some internal states in model_manager/inference_runner might be shared.
    # To be safe and prevent concurrent mutation of global model state:
    with model_lock:
        yield from inference_runner.synthesize_speech(*args, _text_normalizer=_text_normalizer)

def main():
    (demo, backbone_select, codec_select, device_choice, use_lmdeploy_cb,
     custom_backbone_model_id, custom_backbone_base_model, custom_backbone_hf_token,
     btn_load, model_status, voice_select, tab_preset, tab_custom, tabs,
     current_mode_state, text_input, custom_audio, custom_text, generation_mode,
     use_batch, max_batch_size_run, temperature_slider, max_chars_chunk_slider,
     btn_generate, btn_stop, audio_output, status_output, cloning_warning_msg,
     cloning_elements_group, custom_model_group) = ui_builder.build_ui(
         model_manager.BACKBONE_CONFIGS, model_manager.CODEC_CONFIGS,
         DEFAULT_TEXT_GPU, DEFAULT_TEXT_TURBO, model_manager.get_available_devices
     )

    with demo:
        def on_codec_change(codec: str, current_mode: str):
            is_onnx = "onnx" in codec.lower()
            if is_onnx and current_mode == "custom_mode":
                return gr.update(visible=False), gr.update(selected="preset_mode"), "preset_mode"
            return gr.update(visible=not is_onnx), gr.update(), current_mode
        
        codec_select.change(on_codec_change, inputs=[codec_select, current_mode_state], outputs=[tab_custom, tabs, current_mode_state])
        tab_preset.select(lambda: "preset_mode", outputs=current_mode_state)
        tab_custom.select(lambda: "custom_mode", outputs=current_mode_state)
        custom_audio.change(ui_builder.validate_audio_duration, inputs=[custom_audio], outputs=[cloning_warning_msg])
        
        def on_backbone_change(choice):
            is_custom = (choice == "Custom Model")
            is_hw_accel_supported = "(GPU)" in choice or "v2-Turbo" in choice or is_custom
            if is_hw_accel_supported:
                dev_choices = model_manager.get_available_devices()
                initial_dev = "Auto"
            else:
                dev_choices = ["CPU"]
                initial_dev = "CPU"
            
            if "Turbo" in choice:
                codec_update = gr.update(value="VieNeu-Codec", interactive=False)
                text_update = gr.update(value=DEFAULT_TEXT_TURBO)
                temp_update = gr.update(value=0.4)
            else:
                codec_update = gr.update(value="NeuCodec (Distill)", interactive=False)
                text_update = gr.update(value=DEFAULT_TEXT_GPU)
                temp_update = gr.update(value=0.7)
                
            return (gr.update(visible=is_custom), codec_update, text_update, temp_update,
                    gr.update(choices=dev_choices, value=initial_dev), gr.update(visible=True))

        backbone_select.change(on_backbone_change, inputs=[backbone_select], outputs=[custom_model_group, codec_select, text_input, temperature_slider, device_choice, cloning_elements_group])
        
        def on_custom_id_change(model_id):
            if model_id and "lora" in model_id.lower():
                base_model = "VieNeu-TTS-0.3B (GPU)" if "0.3" in model_id else "VieNeu-TTS (GPU)"
                return gr.update(visible=True, value=base_model), gr.update(), gr.update()
            return gr.update(visible=False), gr.update(), gr.update()
            
        custom_backbone_model_id.change(on_custom_id_change, inputs=[custom_backbone_model_id], outputs=[custom_backbone_base_model, custom_audio, custom_text])

        btn_load.click(
            fn=safe_load_model,
            inputs=[backbone_select, codec_select, device_choice, use_lmdeploy_cb,
                    custom_backbone_model_id, custom_backbone_base_model, custom_backbone_hf_token],
            outputs=[model_status, btn_generate, btn_load, btn_stop, voice_select, tab_preset, tab_custom, tabs, current_mode_state]
        )
        
        generate_event = btn_generate.click(
            fn=safe_synthesize_speech,
            inputs=[text_input, voice_select, custom_audio, custom_text, current_mode_state, 
                    generation_mode, use_batch, max_batch_size_run,
                    temperature_slider, max_chars_chunk_slider],
            outputs=[audio_output, status_output]
        )
        
        btn_generate.click(lambda: gr.update(interactive=True), outputs=btn_stop)
        generate_event.then(lambda: gr.update(interactive=False), outputs=btn_stop)
        btn_stop.click(fn=None, cancels=[generate_event])
        btn_stop.click(lambda: (None, "⏹️ Đã dừng tạo giọng nói."), outputs=[audio_output, status_output])
        btn_stop.click(lambda: gr.update(interactive=False), outputs=btn_stop)

        demo.load(fn=model_manager.restore_ui_state, outputs=[model_status, btn_generate, btn_stop])

    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    share = env_bool("GRADIO_SHARE", default=os.getenv("COLAB_RELEASE_TAG") is not None)
    if server_name == "0.0.0.0" and os.getenv("GRADIO_SHARE") is None:
        share = False

    demo.queue().launch(server_name=server_name, server_port=server_port, share=share)

if __name__ == "__main__":
    main()
