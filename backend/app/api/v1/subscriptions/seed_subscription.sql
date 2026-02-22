-- Example SQL Inserts for Subscription Plans (Seed Data)

-- 1. Standard Apartment Monthly Plan
INSERT INTO subscription_plans (
    name, description, category_type, pricing_model, price, billing_cycle,
    max_units, max_members, pickup_limit, waste_weight_limit, driver_limit,
    is_visible, is_active, created_at, updated_at
) VALUES (
    'Standard Apartment Monthly', 'Ideal for mid-sized apartment complexes', 'APARTMENT', 'FIXED', 199.99, 'MONTHLY',
    50, NULL, 4, 1000.0, 1,
    TRUE, TRUE, NOW(), NOW()
);

-- 2. Household Yearly Premium Plan
INSERT INTO subscription_plans (
    name, description, category_type, pricing_model, price, billing_cycle,
    max_units, max_members, pickup_limit, waste_weight_limit, driver_limit,
    is_visible, is_active, created_at, updated_at
) VALUES (
    'Premium Household Yearly', 'Comprehensive coverage for large households', 'HOUSEHOLD', 'FIXED', 499.99, 'YEARLY',
    NULL, 10, 52, 5000.0, 1,
    TRUE, TRUE, NOW(), NOW()
);

-- 3. Commercial Custom Enterprise Plan
INSERT INTO subscription_plans (
    name, description, category_type, pricing_model, price, billing_cycle,
    max_units, max_members, pickup_limit, waste_weight_limit, driver_limit,
    is_visible, is_active, created_at, updated_at
) VALUES (
    'Enterprise Commercial', 'Tailored for large commercial buildings', 'COMMERCIAL', 'CUSTOM', 999.00, 'MONTHLY',
    NULL, NULL, 20, 10000.0, 3,
    TRUE, TRUE, NOW(), NOW()
);

-- Example SQL Insert for a Subscription
-- Note: Replace organization_id (1) and plan_id (1) with actual IDs from your DB
INSERT INTO subscriptions (
    organization_id, plan_id, start_date, end_date, status, auto_renew,
    created_at, updated_at
) VALUES (
    1, 1, NOW(), NOW() + INTERVAL '30 days', 'ACTIVE', TRUE,
    NOW(), NOW()
);

-- Example SQL Insert for Subscription Usage
-- Note: Replace subscription_id (1)
INSERT INTO subscription_usage (
    subscription_id, pickups_used, waste_weight_used, drivers_used,
    last_reset_at, updated_at
) VALUES (
    1, 0, 0.0, 0,
    NOW(), NOW()
);
