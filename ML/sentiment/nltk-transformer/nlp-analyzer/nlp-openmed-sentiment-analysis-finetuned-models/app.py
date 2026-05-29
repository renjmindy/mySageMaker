import os
from ui.app import demo

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.getenv("GRADIO_PORT", 7860)),
    share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
    ssr_mode=False,
)
