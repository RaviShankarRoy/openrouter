package proxy

import (
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/openrouter/gateway-go/internal/service/router"
)

// clientPool keeps one *http.Client per provider with tuned transport.
// HTTP/2 by default; persistent connections; per-host limits configured
// from providers.yaml.
type clientPool struct {
	mu      sync.RWMutex
	clients map[string]*http.Client
	router  *router.Router
}

func newClientPool(r *router.Router) *clientPool {
	return &clientPool{
		clients: make(map[string]*http.Client),
		router:  r,
	}
}

// For returns the cached client for provider, building one on first use.
func (p *clientPool) For(provider string) *http.Client {
	p.mu.RLock()
	c, ok := p.clients[provider]
	p.mu.RUnlock()
	if ok {
		return c
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if c, ok := p.clients[provider]; ok {
		return c
	}
	cfg, _ := p.router.Provider(provider)
	c = &http.Client{
		Timeout: time.Duration(maxInt(cfg.TimeoutSeconds, 60)) * time.Second,
		Transport: &http.Transport{
			Proxy: http.ProxyFromEnvironment,
			DialContext: (&net.Dialer{
				Timeout:   5 * time.Second,
				KeepAlive: 30 * time.Second,
			}).DialContext,
			MaxIdleConns:        maxInt(cfg.MaxIdleConns, 100),
			MaxIdleConnsPerHost: maxInt(cfg.MaxConnsPerHost, 50),
			MaxConnsPerHost:     maxInt(cfg.MaxConnsPerHost, 50),
			IdleConnTimeout:     90 * time.Second,
			ForceAttemptHTTP2:   true,
			TLSHandshakeTimeout: 5 * time.Second,
		},
	}
	p.clients[provider] = c
	return c
}

func maxInt(a, def int) int {
	if a <= 0 {
		return def
	}
	return a
}

// --- Buffer pool for streaming. ---

var bufPool = sync.Pool{
	New: func() any {
		b := make([]byte, 32*1024) // 32KB chunks; tuned via load test
		return &b
	},
}

func getBuffer() []byte {
	return *bufPool.Get().(*[]byte)
}

func putBuffer(b []byte) {
	bufPool.Put(&b)
}
