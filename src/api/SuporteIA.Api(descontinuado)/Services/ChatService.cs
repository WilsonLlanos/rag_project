using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;

namespace SuporteIA.Api.Services;

/// <summary>
/// Serviço responsável pela orquestração da inteligência artificial.
/// Utiliza o SDK Microsoft Semantic Kernel para gerenciar o fluxo RAG.
/// </summary>
public class ChatService
{
    // O Kernel é o objeto central do Semantic Kernel que conecta modelos de IA, conectores e plugins.
    private readonly Kernel _kernel;
    
    // Interface abstrata que permite interagir com diferentes modelos de chat (GPT-4, GPT-3.5, etc).
    private readonly IChatCompletionService _chat;

    /// <summary>
    /// Construtor que recebe o Kernel via Injeção de Dependência.
    /// </summary>
    public ChatService(Kernel kernel)
    {
        _kernel = kernel;
        
        // Extraímos do Kernel o serviço específico de chat que foi configurado no Program.cs.
        // Isso garante que estamos usando as credenciais corretas do Azure OpenAI.
        _chat = kernel.GetRequiredService<IChatCompletionService>();
    }

    /// <summary>
    /// Método assíncrono que processa a dúvida do usuário com base no contexto da tela atual.
    /// </summary>
    /// <param name="pergunta">Texto digitado pelo usuário no frontend (Streamlit).</param>
    /// <param name="telaAtual">Identificação da tela onde o usuário se encontra (ex: Cadastro, Vendas).</param>
    public async Task<string> ObterRespostaSuporteAsync(string pergunta, string telaAtual)
    {
        // O ChatHistory armazena a memória da conversa atual. É aqui que enviamos as instruções de comportamento.
        var historico = new ChatHistory();
        
        // Definição do System Prompt: Aqui definimos a "persona" da IA e injetamos a variável de contexto da tela.
        // O uso de string literal ($""") permite escrever textos longos de forma limpa.
        string systemMessage = $"""
            Você é um assistente de suporte especializado em trading de café.
            O contexto atual é crucial: o usuário está operando na tela "{telaAtual}".
            Sua missão é usar o manual técnico (RAG) para fornecer instruções precisas sobre as regras de negócio.
            Se a dúvida for técnica demais ou não constar no manual, oriente o usuário a ligar para o TI no ramal 500.
            """;

        // Adicionamos a mensagem de sistema (instruções de comportamento) ao início do histórico.
        historico.AddSystemMessage(systemMessage);
        
        // Adicionamos a pergunta real enviada pelo usuário.
        historico.AddUserMessage(pergunta);

        // Chamada assíncrona para a API do Azure OpenAI.
        // O modelo processa o histórico (instruções + pergunta) e gera a melhor resposta.
        var resposta = await _chat.GetChatMessageContentAsync(historico);

        // Convertemos o objeto de resposta da Microsoft para uma string simples que será enviada para o frontend.
        return resposta.ToString();
    }
}