
grammarTable = { "." : ["FILENAME","FILENAME-PATTERN"],
                 # the only toplevel things
                 }

All ::= FileDefinition+
FileDefinition :== SingleFileDef || PatternFileDef
PatternFileDef :== Line("FILENAME-PATTERN",filename) 
SingleFileDef :== Optional(FilterDef)
Filter
