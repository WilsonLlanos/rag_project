using SuporteIA.Api.Services; // Ajuste para o seu namespace se necessário
using Microsoft.SemanticKernel;
using SuporteIA.Api.Plugins;

var builder = WebApplication.CreateBuilder(args);

// --- 1. CONFIGURAÇÃO DOS SERVIÇOS ---

// Adiciona suporte a Controllers (essencial para o seu ChatController funcionar)
builder.Services.AddControllers();

// Adiciona o gerador de documentos Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Registra o nosso ChatService para Injeção de Dependência
builder.Services.AddScoped<ChatService>();

// Configura o Semantic Kernel com os dados do seu appsettings.json
builder.Services.AddKernel()
    .AddAzureOpenAIChatCompletion(
        deploymentName: builder.Configuration["AzureOpenAI:DeploymentName"] ?? "",
        endpoint: builder.Configuration["AzureOpenAI:Endpoint"] ?? "",
        apiKey: builder.Configuration["AzureOpenAI:ApiKey"] ?? ""
    );

var app = builder.Build();

// --- 2. CONFIGURAÇÃO DO PIPELINE (MIDDLEWARE) ---

// Ativa o Swagger apenas em desenvolvimento
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Suporte IA Café v1");
        c.RoutePrefix = "swagger"; // Define que o acesso será em /swagger
    });
}

app.UseHttpsRedirection();

// Importante: Mapeia os Controllers para que a API encontre o ChatController
app.MapControllers();

app.Run();