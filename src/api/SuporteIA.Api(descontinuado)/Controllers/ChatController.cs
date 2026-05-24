using Microsoft.AspNetCore.Mvc;
using SuporteIA.Api.Models;
using SuporteIA.Api.Services;

namespace SuporteIA.Api.Controllers;

// Define a rota base da API como: api/chat
[ApiController]
[Route("api/[controller]")]
public class ChatController : ControllerBase
{
    private readonly ChatService _chatService;

    // O ASP.NET injeta automaticamente o ChatService que registramos no Program.cs
    public ChatController(ChatService chatService)
    {
        _chatService = chatService;
    }

    /// <summary>
    /// Endpoint POST que recebe a dúvida do usuário e processa via IA.
    /// Exemplo de chamada: POST /api/chat/pergunta
    /// </summary>
    [HttpPost("pergunta")]
    public async Task<IActionResult> PostPergunta([FromBody] ChatRequest request)
    {
        // Validação básica: se a pergunta estiver vazia, retorna erro 400 (Bad Request)
        if (string.IsNullOrEmpty(request.Pergunta))
        {
            return BadRequest("A pergunta não pode estar vazia.");
        }

        try
        {
            // Chama o nosso Service para processar a lógica da IA
            var resposta = await _chatService.ObterRespostaSuporteAsync(request.Pergunta, request.TelaAtual);
            
            // Retorna a resposta com status 200 (OK)
            return Ok(new { resposta });
        }
        catch (Exception ex)
        {
            // Em caso de erro técnico, retorna status 500 para o frontend
            return StatusCode(500, $"Erro interno no processamento da IA: {ex.Message}");
        }
    }
}