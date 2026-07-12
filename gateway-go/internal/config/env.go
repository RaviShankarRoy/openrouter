package config

import "os"

func getenvStdlib(k string) string { return os.Getenv(k) }
