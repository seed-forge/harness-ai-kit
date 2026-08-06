# Key Naming Conventions

## Format
`{namespace}:{entity_type}:{entity_id}:{attribute}`

## Examples
```
user:1001:profile        # Hash with user profile fields
user:1001:sessions       # Set of active session IDs
session:abc123           # Hash with session data
order:2024:items         # List of order items
game:space-invaders:leaderboard  # Sorted Set
```

## Multi-tenancy
Prefix with tenant: `tenant:42:user:7:cart`

## Cleanup Examples
Bad: `User_1001_Profile`, `user-1001`, `http://example.com/users/1001`
Good: `user:1001:profile`

## Edge Cases
- Keys with special characters: avoid spaces, use colons
- Very long keys: use a hash digest (e.g., MD5 of URL)
- Temporary keys: prefix with `tmp:` and set short TTL
