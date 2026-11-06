# SIA-app
Sistemas  de tickets EMI

## Asistente de IA local (Ollama)

El modelo `sigta-ai` no se versiona: sus pesos pesan unos 2 GB y GitHub no
acepta archivos de más de 100 MB. Se reconstruye en el equipo anfitrión a
partir del `Modelfile` de la raíz:

```powershell
ollama pull llama3.2:3b
ollama create sigta-ai -f ./Modelfile
ollama run sigta-ai "¿Qué hago si mi cuenta está bloqueada?"
```

Para que las máquinas virtuales lo consulten, Ollama debe escuchar en la red
(`OLLAMA_HOST=0.0.0.0:11434`) y el backend debe apuntar a la IP del anfitrión
con `OLLAMA_URL` (ver `deploy/env/sia.env.example`).
