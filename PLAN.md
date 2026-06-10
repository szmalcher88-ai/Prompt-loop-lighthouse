# Plan zadań pętli — model 3D latarni morskiej

<!-- Format: jedna linia = jedno zadanie = jeden commit.
     - [ ] otwarte, [x] zrobione (oznacza pętla), [!] eskalowane.
     Ten plik należy do pętli. Agent ma zakaz go dotykać (guard automatyczny). -->

- [x] Utwórz lighthouse.py (czysty Python, stdlib-only), który po `python lighthouse.py` zapisuje out/lighthouse.obj — model 3D latarni morskiej w układzie Y-up z nazwanymi grupami `o`: base (skalisty cokół), tower (cylindryczna wieża zwężająca się ku górze, min. 24 segmenty obwodu), gallery (galeryjka z balustradą pod laterną), lantern (przeszklona laterna), roof (stożkowy dach jako najwyższy punkt modelu), door (drzwi w dolnej części wieży); PRZED pisaniem przeczytaj scripts/check_lighthouse.py i spełnij wszystkie jego asercje geometryczne.
- [ ] Rozszerz lighthouse.py o materiały: generuj dodatkowo out/lighthouse.mtl z co najmniej 3 materiałami (newmtl + kolory Kd, np. biały i czerwony pas, szkło laterny, ciemny dach), w OBJ dodaj `mtllib lighthouse.mtl` oraz `usemtl`, w tym co najmniej 2 naprzemienne materiały pasów na grupie tower — zgodnie z sekcją materiałów w scripts/check_lighthouse.py.
