---
trigger: always_on
---

Padrões Utilizados:

- CQRS (Command Query Responsibility Segregation) - Repositórios separados em read/ e write/
- Domain-Driven Design - Lógica organizada por domínios de negócio
- UseCase Pattern - Cada ação de negócio é um ficheiro separado
- Unit of Work - Gestão de transações centralizada


Seguir a estrutura que temos definida:

- Routes simples e limpas
- Usecases Orquestram logica
- Services, pedaços de codigo reutilizaveis
- Models, modelos de base de dados
- Schemas metodos para respostas e inputs


Importante:

- Usecase não podem mexer diretamente com o modelo da base de dados, apenas com repositorios
- Manter arquitetura CORS para repositorios
