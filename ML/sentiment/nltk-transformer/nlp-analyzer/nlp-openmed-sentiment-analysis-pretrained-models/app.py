import os
from ui.app import demo

_on_spaces = os.getenv("SPACE_ID") is not None

demo.launch(
    server_name="0.0.0.0" if not _on_spaces else None,
    server_port=int(os.getenv("GRADIO_PORT", 7860)) if not _on_spaces else None,
    share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
    ssr_mode=False,
)
