import time
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
import nltk
from nltk.tokenize import sent_tokenize
import gradio as gr

nltk.download('punkt')

class DipperParaphraser(object):
    def __init__(self, model="kalpeshk2011/dipper-paraphraser-xxl", verbose=True):
        time1 = time.time()
        self.tokenizer = T5Tokenizer.from_pretrained('google/t5-v1_1-xxl')
        self.model = T5ForConditionalGeneration.from_pretrained(model)
        if verbose:
            print(f"{model} model loaded in {time.time() - time1}")
        self.model.cuda()
        self.model.eval()

    def paraphrase(self, input_text, lex_diversity, order_diversity, prefix="Paraphrasing", sent_interval=3, **kwargs):
        """Paraphrase a text using the DIPPER model.

        Args:
            input_text (str): The text to paraphrase. Make sure to mark the sentence to be paraphrased between <sent> and </sent> blocks, keeping space on either side.
            lex_diversity (int): The lexical diversity of the output, choose multiples of 20 from 0 to 100. 0 means no diversity, 100 means maximum diversity.
            order_diversity (int): The order diversity of the output, choose multiples of 20 from 0 to 100. 0 means no diversity, 100 means maximum diversity.
            **kwargs: Additional keyword arguments like top_p, top_k, max_length.
        """
        assert lex_diversity in [0, 20, 40, 60, 80, 100], "Lexical diversity must be one of 0, 20, 40, 60, 80, 100."
        assert order_diversity in [0, 20, 40, 60, 80, 100], "Order diversity must be one of 0, 20, 40, 60, 80, 100."

        lex_code = int(100 - lex_diversity)
        order_code = int(100 - order_diversity)

        input_text = " ".join(input_text.split())
        sentences = sent_tokenize(input_text)
        prefix = " ".join(prefix.replace("\n", " ").split())
        output_text = ""

        for sent_idx in range(0, len(sentences), sent_interval):
            curr_sent_window = " ".join(sentences[sent_idx:sent_idx + sent_interval])
            final_input_text = f"lexical = {lex_code}, order = {order_code}"
            if prefix:
                final_input_text += f" {prefix}"
            final_input_text += f" <sent> {curr_sent_window} </sent>"

            final_input = self.tokenizer([final_input_text], return_tensors="pt")
            final_input = {k: v.cuda() for k, v in final_input.items()}

            with torch.inference_mode():
                outputs = self.model.generate(**final_input, **kwargs)
            outputs = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            prefix += " " + outputs[0]
            output_text += " " + outputs[0]

        return output_text

# Initialiser le paraphraseur
dp = DipperParaphraser(model="kalpeshk2011/dipper-paraphraser-xxl")

# Fonction Gradio pour paraphraser
def gradio_paraphrase(input_text, lex_diversity, order_diversity, top_p, top_k, max_length):
    return dp.paraphrase(
        input_text, 
        lex_diversity=int(lex_diversity), 
        order_diversity=int(order_diversity),
        sent_interval=3, 
        do_sample=True, 
        top_p=float(top_p), 
        top_k=int(top_k), 
        max_length=int(max_length)
    )

# Créer l'interface Gradio
iface = gr.Interface(
    fn=gradio_paraphrase, 
    inputs=[
        gr.inputs.Textbox(lines=5, placeholder="Entrez le texte à paraphraser ici..."), 
        gr.inputs.Slider(minimum=0, maximum=100, step=20, default=80, label="Diversité lexicale"),
        gr.inputs.Slider(minimum=0, maximum=100, step=20, default=60, label="Diversité de l'ordre"),
        gr.inputs.Slider(minimum=0.1, maximum=1.0, step=0.05, default=0.75, label="Top-p"),
        gr.inputs.Slider(minimum=0, maximum=100, step=1, default=50, label="Top-k"),
        gr.inputs.Slider(minimum=1, maximum=512, step=1, default=512, label="Longueur maximale")
    ], 
    outputs="text",
    title="Paraphraseur de Texte",
    description="Utilisez cette interface pour paraphraser du texte en utilisant le modèle DIPPER."
)

# Lancer l'interface
iface.launch()