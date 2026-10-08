# Hitta skyddsrum: stängd-lista

Listan över tillfälligt begränsade skyddsrum i Sverige, som appen Hitta skyddsrum hämtar varje natt.

**Adress:** https://emilalm.github.io/hitta-skyddsrum-data/begransade.json

```json
{"schema":1,"dataDate":"2026-10-06","generated":"…","source":"Myndigheten för civilt försvar (MCF)","closed":["100022-1", …]}
```

- `dataDate`: datumet för MCF:s data.
- `closed`: skyddsrumsnummer (SkrNr) som är tillfälligt begränsade.

Källa: Myndigheten för civilt försvar (MCF), skyddsrummens öppna visningstjänst (`https://inspire.mcf.se/skyddsrum/wfs`). Listan uppdateras automatiskt varje natt. Varje version finns kvar i historiken.

Det här är inte en tjänst från MCF. Uppgifterna om ett skyddsrum ska kontrolleras hos MCF eller kommunen.
