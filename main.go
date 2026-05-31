package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/gorilla/websocket"
)

type Client struct {
	Conn *websocket.Conn
	Room string
}

type Message struct {
	Name    string `json:"name"`
	Message string `json:"message"`
	Type    string `json:"type"`
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

var (
	rooms = make(map[string]map[*websocket.Conn]bool)
	mutex sync.Mutex
)

func home(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, `{"status":"online","app":"Walkie Talkie Messenger","message":"Servidor funcionando"}`)
}

func handleConnections(w http.ResponseWriter, r *http.Request) {
	freq := r.URL.Query().Get("freq")
	name := r.URL.Query().Get("name")

	if freq == "" {
		http.Error(w, "Frequência obrigatória. Use ?freq=suaFrequencia", http.StatusBadRequest)
		return
	}

	if name == "" {
		name = "Usuário"
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("Erro ao conectar:", err)
		return
	}

	mutex.Lock()
	if rooms[freq] == nil {
		rooms[freq] = make(map[*websocket.Conn]bool)
	}
	rooms[freq][conn] = true
	mutex.Unlock()

	log.Printf("%s conectado na frequência: %s\n", name, freq)

	sendSystemMessage(freq, fmt.Sprintf("%s entrou na frequência.", name))

	defer func() {
		mutex.Lock()
		delete(rooms[freq], conn)

		if len(rooms[freq]) == 0 {
			delete(rooms, freq)
		}

		mutex.Unlock()

		conn.Close()

		log.Printf("%s desconectou da frequência: %s\n", name, freq)
		sendSystemMessage(freq, fmt.Sprintf("%s saiu da frequência.", name))
	}()

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Println("Usuário desconectado:", err)
			break
		}

		var received Message
		err = json.Unmarshal(msg, &received)
		if err != nil {
			log.Println("Mensagem inválida:", err)
			continue
		}

		received.Type = "message"

		broadcast(freq, received)
	}
}

func sendSystemMessage(freq string, text string) {
	msg := Message{
		Name:    "Sistema",
		Message: text,
		Type:    "system",
	}

	broadcast(freq, msg)
}

func broadcast(freq string, msg Message) {
	data, err := json.Marshal(msg)
	if err != nil {
		log.Println("Erro ao converter mensagem:", err)
		return
	}

	mutex.Lock()
	defer mutex.Unlock()

	for conn := range rooms[freq] {
		err := conn.WriteMessage(websocket.TextMessage, data)
		if err != nil {
			log.Println("Erro ao enviar mensagem:", err)
			conn.Close()
			delete(rooms[freq], conn)
		}
	}
}

func main() {
	http.HandleFunc("/", home)
	http.HandleFunc("/ws", handleConnections)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Println("Servidor ativo na porta", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
