namespace SuporteIA.Api.Models;

// Esta classe define o formato do JSON que o Streamlit enviará para a API
public class ChatRequest
{
    public string Pergunta { get; set; } = string.Empty;
    public string TelaAtual { get; set; } = string.Empty;
}