//! WoT Form Worker
//!
//! Cloudflare Worker handling form submissions for:
//! - now.pub (identity name reservations)
//! - wot.rocks (waitlist signups)
//! - wot.technology (SDK early access)

use serde::{Deserialize, Serialize};
use worker::*;

/// Form submission from now.pub - identity name reservation
#[derive(Debug, Deserialize, Serialize)]
struct NowPubSignup {
    subdomain: String,
    email: String,
    #[serde(default)]
    pubkey: Option<String>,
}

/// Form submission from wot.rocks - waitlist
#[derive(Debug, Deserialize, Serialize)]
struct WotRocksSignup {
    email: String,
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    use_case: Option<String>,
}

/// Form submission from wot.technology - SDK access
#[derive(Debug, Deserialize, Serialize)]
struct WotTechnologySignup {
    email: String,
    #[serde(default)]
    github_username: Option<String>,
    #[serde(default)]
    interest: Option<String>,
}

/// Unified storage record
#[derive(Debug, Serialize)]
struct SignupRecord {
    source: String,
    email: String,
    timestamp: String,
    data: serde_json::Value,
}

/// API response
#[derive(Debug, Serialize)]
struct ApiResponse {
    success: bool,
    message: String,
}

fn log_request(req: &Request) {
    console_log!(
        "{} - [{}] \"{}\"",
        Date::now().to_string(),
        req.method().to_string(),
        req.path(),
    );
}

fn cors_headers(origin: &str, allowed_origins: &str) -> Headers {
    let mut headers = Headers::new();

    // Check if origin is in allowed list
    let is_allowed = allowed_origins
        .split(',')
        .any(|o| o.trim() == origin || o.trim() == "*");

    if is_allowed {
        headers.set("Access-Control-Allow-Origin", origin).unwrap();
    }

    headers
        .set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        .unwrap();
    headers
        .set("Access-Control-Allow-Headers", "Content-Type")
        .unwrap();
    headers.set("Access-Control-Max-Age", "86400").unwrap();

    headers
}

fn json_response(data: &impl Serialize, status: u16, headers: Headers) -> Result<Response> {
    let json = serde_json::to_string(data)?;
    let mut response = Response::ok(json)?;

    // Copy headers
    for (key, value) in headers.entries() {
        response.headers_mut().set(&key, &value)?;
    }

    response.headers_mut().set("Content-Type", "application/json")?;

    Ok(response.with_status(status))
}

async fn handle_now_pub_signup(
    mut req: Request,
    kv: kv::KvStore,
    headers: Headers,
) -> Result<Response> {
    let signup: NowPubSignup = req.json().await?;

    // Validate subdomain (alphanumeric, hyphens, 3-30 chars)
    if signup.subdomain.len() < 3 || signup.subdomain.len() > 30 {
        return json_response(
            &ApiResponse {
                success: false,
                message: "Subdomain must be 3-30 characters".into(),
            },
            400,
            headers,
        );
    }

    if !signup
        .subdomain
        .chars()
        .all(|c| c.is_alphanumeric() || c == '-')
    {
        return json_response(
            &ApiResponse {
                success: false,
                message: "Subdomain can only contain letters, numbers, and hyphens".into(),
            },
            400,
            headers,
        );
    }

    // Check if subdomain is already reserved
    let key = format!("nowpub:subdomain:{}", signup.subdomain.to_lowercase());
    if kv.get(&key).text().await?.is_some() {
        return json_response(
            &ApiResponse {
                success: false,
                message: "This subdomain is already reserved".into(),
            },
            409,
            headers,
        );
    }

    // Store the reservation
    let record = SignupRecord {
        source: "now.pub".into(),
        email: signup.email.clone(),
        timestamp: Date::now().to_string(),
        data: serde_json::to_value(&signup)?,
    };

    kv.put(&key, serde_json::to_string(&record)?)?
        .execute()
        .await?;

    // Also store by email for lookup
    let email_key = format!("nowpub:email:{}", signup.email.to_lowercase());
    kv.put(&email_key, &signup.subdomain)?
        .execute()
        .await?;

    json_response(
        &ApiResponse {
            success: true,
            message: format!("{}.now.pub has been reserved!", signup.subdomain),
        },
        200,
        headers,
    )
}

async fn handle_wot_rocks_signup(
    mut req: Request,
    kv: kv::KvStore,
    headers: Headers,
) -> Result<Response> {
    let signup: WotRocksSignup = req.json().await?;

    // Store by email
    let key = format!("wotrocks:email:{}", signup.email.to_lowercase());

    let record = SignupRecord {
        source: "wot.rocks".into(),
        email: signup.email.clone(),
        timestamp: Date::now().to_string(),
        data: serde_json::to_value(&signup)?,
    };

    kv.put(&key, serde_json::to_string(&record)?)?
        .execute()
        .await?;

    json_response(
        &ApiResponse {
            success: true,
            message: "You're on the waitlist! We'll be in touch.".into(),
        },
        200,
        headers,
    )
}

async fn handle_wot_technology_signup(
    mut req: Request,
    kv: kv::KvStore,
    headers: Headers,
) -> Result<Response> {
    let signup: WotTechnologySignup = req.json().await?;

    // Store by email
    let key = format!("wottech:email:{}", signup.email.to_lowercase());

    let record = SignupRecord {
        source: "wot.technology".into(),
        email: signup.email.clone(),
        timestamp: Date::now().to_string(),
        data: serde_json::to_value(&signup)?,
    };

    kv.put(&key, serde_json::to_string(&record)?)?
        .execute()
        .await?;

    json_response(
        &ApiResponse {
            success: true,
            message: "You're on the early access list for the SDK!".into(),
        },
        200,
        headers,
    )
}

#[event(fetch)]
async fn main(req: Request, env: Env, _ctx: Context) -> Result<Response> {
    console_error_panic_hook::set_once();
    log_request(&req);

    let allowed_origins = env.var("CORS_ORIGIN")?.to_string();
    let origin = req
        .headers()
        .get("Origin")?
        .unwrap_or_else(|| "*".to_string());

    let headers = cors_headers(&origin, &allowed_origins);

    // Handle CORS preflight
    if req.method() == Method::Options {
        return Response::empty()?.with_headers(headers);
    }

    let kv = env.kv("WOT_SIGNUPS")?;

    Router::with_data((kv, headers.clone()))
        .get("/", |_, _| Response::ok("WoT Form Worker v0.1.0"))
        .get("/health", |_, _| {
            Response::ok(r#"{"status":"healthy"}"#)
        })
        .post_async("/api/now-pub/signup", |req, ctx| async move {
            let (kv, headers) = ctx.data;
            handle_now_pub_signup(req, kv.clone(), headers.clone()).await
        })
        .post_async("/api/wot-rocks/signup", |req, ctx| async move {
            let (kv, headers) = ctx.data;
            handle_wot_rocks_signup(req, kv.clone(), headers.clone()).await
        })
        .post_async("/api/wot-technology/signup", |req, ctx| async move {
            let (kv, headers) = ctx.data;
            handle_wot_technology_signup(req, kv.clone(), headers.clone()).await
        })
        // List signups (protected - add auth in production)
        .get_async("/api/signups/:source", |_req, ctx| async move {
            let (kv, headers) = ctx.data;
            let source = ctx.param("source").unwrap();

            let prefix = match source.as_str() {
                "now-pub" => "nowpub:",
                "wot-rocks" => "wotrocks:",
                "wot-technology" => "wottech:",
                _ => {
                    return json_response(
                        &ApiResponse {
                            success: false,
                            message: "Unknown source".into(),
                        },
                        404,
                        headers.clone(),
                    )
                }
            };

            let list = kv.list().prefix(prefix.into()).execute().await?;
            let keys: Vec<String> = list.keys.into_iter().map(|k| k.name).collect();

            let mut entries = Vec::new();
            for key in keys {
                if let Some(value) = kv.get(&key).text().await? {
                    entries.push(serde_json::from_str::<serde_json::Value>(&value)?);
                }
            }

            json_response(&entries, 200, headers.clone())
        })
        .run(req, env)
        .await
}
