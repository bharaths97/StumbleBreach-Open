# skill-library/

Optional. A lookup shelf for full vendor skill repos relevant to this
competition (methodology/payload references) — never auto-loaded into
a session's context. Sessions read from it on demand.

```
skill-library/
├── INDEX.md              ← catalog, cheap to read in full
└── vendor/
    └── <repo-name>/      (raw clone, untouched)
```

If this engagement doesn't need external skill repos, leave this
directory empty (just this README and `INDEX.md`) — nothing else
references it, and `RULES.md` treats it as optional.

## How a session should use this

1. Check `INDEX.md` — it's small, safe to read in full without bloating
   context.
2. If something in it looks relevant to the current task, **tell the
   user** what you found and how you intend to use it before doing
   anything else.
3. Read just the specific file(s) needed for this task. Nothing gets
   copied anywhere — it's a one-off read, every time a session needs it,
   not a one-time promotion.

This keeps every session's default context lean: the index costs almost
nothing to read, and full skill content only ever loads when a session
actually needs it for the task at hand.
