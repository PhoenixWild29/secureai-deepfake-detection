use anchor_lang::prelude::*;

declare_id!("YourProgramIdHere");  // Replace with your actual program ID after building

#[program]
pub mod secure_ai_detector {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, video_hash: String, authenticity_score: u64) -> Result<()> {
        let storage_account = &mut ctx.accounts.storage_account;
        storage_account.video_hash = video_hash;
        storage_account.authenticity_score = authenticity_score;
        msg!("Stored video hash: {} and authenticity score: {}!", video_hash, authenticity_score);
        Ok(())
    }

    pub fn update(ctx: Context<Update>, new_video_hash: String, new_authenticity_score: u64) -> Result<()> {
        let storage_account = &mut ctx.accounts.storage_account;
        storage_account.video_hash = new_video_hash;
        storage_account.authenticity_score = new_authenticity_score;
        msg!("Updated video hash: {} and authenticity score: {}!", new_video_hash, new_authenticity_score);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(init, payer = signer, space = 8 + 4 + 256 + 8)]
    pub storage_account: Account<'info, StorageAccount>,
    #[account(mut)]
    pub signer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Update<'info> {
    #[account(mut)]
    pub storage_account: Account<'info, StorageAccount>,
}

#[account]
pub struct StorageAccount {
    pub video_hash: String,
    pub authenticity_score: u64,
}