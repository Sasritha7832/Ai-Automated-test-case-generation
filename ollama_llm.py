# ollama_llm.py
import ollama

class OllamaLLM:
    def __init__(self, model="ollama/gemma3:4b", temperature=0.3, top_p=0.9):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p

    def run(self, text: str) -> str:
        try:
            response = ollama.generate(
                model=self.model,
                prompt=text,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": 1024
                }
            )
            return response["response"]
        except Exception as e:
            print("Ollama Error:", e)
            return "Error generating response."

    def __call__(self, text: str) -> str:
        return self.run(text)

    def invoke(self, text: str) -> str:
        return self.run(text)