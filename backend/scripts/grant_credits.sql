-- Replace target_email, grant_amount and operation_key, then execute the whole transaction.
BEGIN;

DO $$
DECLARE
    target_email text := 'user@example.com';
    grant_amount bigint := 1000;
    operation_key text := 'manual:20260724:user@example.com:1000';
    account users%ROWTYPE;
BEGIN
    IF grant_amount <= 0 THEN
        RAISE EXCEPTION 'grant_amount must be greater than 0';
    END IF;

    UPDATE users
    SET credit_balance = credit_balance + grant_amount
    WHERE email = target_email
    RETURNING * INTO account;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'user not found: %', target_email;
    END IF;

    INSERT INTO credit_ledger (
        id, user_id, entry_type, amount, balance_after, frozen_after,
        idempotency_key, note, created_at
    ) VALUES (
        gen_random_uuid(), account.id, 'adjustment', grant_amount,
        account.credit_balance, account.credit_frozen, operation_key,
        'MVP 手工发放积分', now()
    );
END $$;

COMMIT;
