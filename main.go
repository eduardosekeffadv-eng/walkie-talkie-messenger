package main

import (
    "fmt"
    "log"
    "net/http"

    "github.com/gorilla/websocket"
)

// estrutura do websocket
var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool { return true },
}

// cada frequência é uma “sala”
var rooms = make(map[string][]*websocket.Conn)

// gerencia as conexões
func handleConnections(w http.ResponseWriter, r *http.Request) {
    freq := r.URL.Query().Get("freq")
    if freq == "" {
        http.Error(w, "Frequência obrigatória (?freq=123)", http.StatusBadRequest)
        return
    }

    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println("Erro ao conectar:", err)
        return
    }
    defer conn.Close()

    rooms[freq] = append(rooms[freq], conn)
    log.Println("Usuário conectado na frequência:", freq)

    for {
        _, msg, err := conn.ReadMessage()
        if err != nil {
            log.Println("Usuário desconectado:", err)
            break
        }

        // retransmite a mensagem pra todos na mesma frequência
        for _, c := range rooms[freq] {
            if err := c.WriteMessage(websocket.TextMessage, msg); err != nil {
                log.Println("Erro ao enviar:", err)
            }
        }
    }
}

func main() {
    http.HandleFunc("/ws", handleConnections)
    fmt.Println("Servidor ativo em porta 8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}